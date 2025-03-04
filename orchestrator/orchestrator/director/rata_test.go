package director_test

import (
	"context"
	"os"
	"testing"
	"time"

	"gitlab.com/isard/isardvdi-sdk-go"
	apiMock "gitlab.com/isard/isardvdi-sdk-go/mock"
	"gitlab.com/isard/isardvdi/orchestrator/cfg"
	"gitlab.com/isard/isardvdi/orchestrator/orchestrator/director"
	operationsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/operations/v1"

	"github.com/rs/zerolog"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestRataNeedToScaleHypervisors(t *testing.T) {
	assert := assert.New(t)

	cases := map[string]struct {
		AvailHypers               []*operationsv1.ListHypervisorsResponseHypervisor
		Hypers                    []*isardvdi.OrchestratorHypervisor
		RataMinCPU                int
		RataMinRAM                int
		RataMaxCPU                int
		RataMaxRAM                int
		RataMinRAMLimitPercent    int
		RataMinRAMLimitMargin     int
		RataMaxRAMLimitPercent    int
		RataMaxRAMLimitMargin     int
		RataHyperMinRAM           int
		RataHyperMaxRAM           int
		ExpectedErr               string
		ExpectedRemoveDeadRow     []string
		ExpectedCreateHypervisor  *operationsv1.CreateHypervisorsRequest
		ExpectedAddDeadRow        []string
		ExpectedDestroyHypervisor *operationsv1.DestroyHypervisorsRequest
	}{
		"if there's enough RAM, it should return 0": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  150,
					Free:  150,
				},
			}},
			RataMinRAM: 100,
		},
		"if there's not enough RAM, it should return the ID of the hypervisor that needs to be created": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:    "testing",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   5000,
			}, {
				Id:    "HUGE HYPERVISOR",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   99999999,
			}, {
				Id:    "already",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   300,
			}},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:         "already",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}},
			RataMinRAM: 500,
			ExpectedCreateHypervisor: &operationsv1.CreateHypervisorsRequest{
				Ids: []string{"testing"},
			},
		},
		"if some hyperviosrs are offline, buffer, GPU only, or only forced don't cound them": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:    "testing",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   5000,
			}, {
				Id:    "HUGE HYPERVISOR",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   99999999,
			}, {
				Id:    "already",
				State: operationsv1.HypervisorState_HYPERVISOR_STATE_AVAILABLE_TO_CREATE,
				Ram:   300,
			}},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:         "already",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}, {
				ID:         "offline",
				Status:     isardvdi.HypervisorStatusOffline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 1000,
					Used:  10,
					Free:  990,
				},
			}, {
				ID:         "buffering",
				Status:     isardvdi.HypervisorStatusOnline,
				Buffering:  true,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 1000,
					Used:  10,
					Free:  990,
				},
			}, {
				ID:         "only forced",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 1000,
					Used:  10,
					Free:  990,
				},
			}, {
				ID:         "gpu only",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				GPUOnly:    true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 1000,
					Used:  10,
					Free:  990,
				},
			}},
			RataMinRAM: 500,
			ExpectedCreateHypervisor: &operationsv1.CreateHypervisorsRequest{
				Ids: []string{"testing"},
			},
		},
		"if there's too much free RAM, it should add the biggest hypervisor that it can to the dead row": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "1",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 500,
					Used:  100,
					Free:  400,
				},
			}, {
				ID:                  "2",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:                  "3",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  100,
					Free:  200,
				},
			}},
			RataMaxRAM:         300,
			ExpectedAddDeadRow: []string{"2"},
		},
		"if there's not enough RAM but there are hypervisors on the dead row, it should remove those from it": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:  "testing",
				Ram: 5000,
			}, {
				Id:  "HUGE HYPERVISOR",
				Ram: 99999999,
			}},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:         "existing-1",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}, {
				ID:                  "existing-2",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          true,
				DesktopsStarted:     20,
				OrchestratorManaged: true,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 3000,
					Used:  2000,
					Free:  1000,
				},
			}},
			RataMinRAM:            500,
			ExpectedRemoveDeadRow: []string{"existing-2"},
		},
		"if there's not enough RAM and there are multiple hypervisors on the dead row, it should remove the smallest hypervisor from it": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{{
				Id:  "testing",
				Ram: 5000,
			}, {
				Id:  "HUGE HYPERVISOR",
				Ram: 99999999,
			}},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "existing-1",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 300,
					Used:  200,
					Free:  100,
				},
			}, {
				ID:                  "existing-2",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          true,
				OrchestratorManaged: true,
				DesktopsStarted:     20,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 3000,
					Used:  2000,
					Free:  1000,
				},
			}, {
				ID:                  "existing-3",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          true,
				OrchestratorManaged: true,
				DesktopsStarted:     20,
				DestroyTime:         time.Now().Add(time.Hour),
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 1000,
					Used:  300,
					Free:  700,
				},
			}},
			RataMinRAM:            500,
			ExpectedRemoveDeadRow: []string{"existing-3"},
		},
		"if there's an hypervisor that's been too much time on the dead row, KILL THEM!! >:(": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:         "1",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 500,
					Used:  400,
					Free:  100,
				},
			}, {
				ID:                  "2",
				Status:              isardvdi.HypervisorStatusOnline,
				DestroyTime:         time.Now().Add(-2 * director.DeadRowDuration),
				DesktopsStarted:     254,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:         "3",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 500,
					Used:  250,
					Free:  250,
				},
			}},
			RataMinRAM: 300,
			ExpectedDestroyHypervisor: &operationsv1.DestroyHypervisorsRequest{
				Ids: []string{"2"},
			},
		},
		"if there's an hypervisor that's in the dead row and has 0 desktops started, KILL THEM!! >:(": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:         "1",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 500,
					Used:  400,
					Free:  100,
				},
			}, {
				ID:                  "2",
				Status:              isardvdi.HypervisorStatusOnline,
				DestroyTime:         time.Now().Add(2 * director.DeadRowDuration),
				DesktopsStarted:     0,
				OnlyForced:          true,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}, {
				ID:         "3",
				Status:     isardvdi.HypervisorStatusOnline,
				OnlyForced: false,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 500,
					Used:  250,
					Free:  250,
				},
			}},
			RataMinRAM: 300,
			ExpectedDestroyHypervisor: &operationsv1.DestroyHypervisorsRequest{
				Ids: []string{"2"},
			},
		},
		"if there aren't enough ram, but there's a small hyper in the dead row and with it the system can work, remove it from the dead row": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "1",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          true,
				DestroyTime:         time.Now().Add(2 * director.DeadRowDuration),
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 600,
					Used:  400,
					Free:  200,
				},
			}, {
				ID:                  "2",
				Status:              isardvdi.HypervisorStatusOnline,
				DesktopsStarted:     0,
				OnlyForced:          false,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 700,
					Used:  100,
					Free:  600,
				},
			}},
			RataMinRAM:            700,
			ExpectedRemoveDeadRow: []string{"1"},
		},
		"regression test #1": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "bm-e4-01",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				DesktopsStarted:     10,
				MinFreeMemGB:        190,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 2051961,
					Used:  67556,
					Free:  1984404,
				},
			}, {
				ID:                  "bm-e2-02",
				Status:              isardvdi.HypervisorStatusOnline,
				DesktopsStarted:     2,
				OnlyForced:          false,
				OrchestratorManaged: false,
				MinFreeMemGB:        47,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 515855,
					Used:  65620,
					Free:  450234,
				},
			}},
			RataMinRAMLimitPercent: 150,
			RataMinRAMLimitMargin:  1,
			RataMaxRAMLimitPercent: 150,
			RataMaxRAMLimitMargin:  112640,
			RataHyperMinRAM:        51200,
			RataHyperMaxRAM:        102400,
			ExpectedAddDeadRow:     []string{"bm-e4-01"},
		},
		"regression test #2": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "bm-e4-04",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				OrchestratorManaged: true,
				DesktopsStarted:     46,
				MinFreeMemGB:        180,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 2051975,
					Used:  232253,
					Free:  1819722,
				},
			}, {
				ID:                  "bm-e2-02",
				Status:              isardvdi.HypervisorStatusOnline,
				DesktopsStarted:     18,
				OnlyForced:          false,
				OrchestratorManaged: false,
				MinFreeMemGB:        47,
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 515855,
					Used:  125714,
					Free:  390140,
				},
			}},
			RataMinRAMLimitPercent: 150,
			RataMinRAMLimitMargin:  1,

			RataMaxRAMLimitPercent: 150,
			RataMaxRAMLimitMargin:  112640,

			RataHyperMinRAM: 51200,
			RataHyperMaxRAM: 102400,

			ExpectedAddDeadRow: []string{"bm-e4-04"},
		},
		"regression test #3": {
			AvailHypers: []*operationsv1.ListHypervisorsResponseHypervisor{},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "bm-e4-01",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				Buffering:           false,
				DestroyTime:         time.Time{},
				BookingsEndTime:     time.Time{},
				OrchestratorManaged: true,
				GPUOnly:             false,
				DesktopsStarted:     57,
				MinFreeMemGB:        190,
				CPU: isardvdi.OrchestratorResourceLoad{
					Total: 100,
					Used:  6,
					Free:  94,
				},
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 2051961,
					Used:  305801,
					Free:  1746160,
				},
			}, {
				ID:                  "bm-e2-02",
				Status:              isardvdi.HypervisorStatusOnline,
				OnlyForced:          false,
				Buffering:           false,
				DestroyTime:         time.Time{},
				BookingsEndTime:     time.Time{},
				OrchestratorManaged: false,
				GPUOnly:             false,
				DesktopsStarted:     23,
				MinFreeMemGB:        47,
				CPU: isardvdi.OrchestratorResourceLoad{
					Total: 100,
					Used:  7,
					Free:  93,
				},
				RAM: isardvdi.OrchestratorResourceLoad{
					Total: 515855,
					Used:  160998,
					Free:  354856,
				},
			}},
			RataMinRAMLimitPercent: 150,
			RataMinRAMLimitMargin:  1,

			RataMaxRAMLimitPercent: 150,
			RataMaxRAMLimitMargin:  112640,

			RataHyperMinRAM: 51200,
			RataHyperMaxRAM: 102400,

			ExpectedAddDeadRow: []string{"bm-e4-01"},
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)

			rata := director.NewRata(cfg.DirectorRata{
				MinCPU:             tc.RataMinCPU,
				MinRAM:             tc.RataMinRAM,
				MaxCPU:             tc.RataMaxCPU,
				MaxRAM:             tc.RataMaxRAM,
				MinRAMLimitPercent: tc.RataMinRAMLimitPercent,
				MinRAMLimitMargin:  tc.RataMinRAMLimitMargin,
				MaxRAMLimitPercent: tc.RataMaxRAMLimitPercent,
				MaxRAMLimitMargin:  tc.RataMaxRAMLimitMargin,
				HyperMinRAM:        tc.RataHyperMinRAM,
				HyperMaxRAM:        tc.RataHyperMaxRAM,
			}, false, &log, nil)

			create, destroy, removeDeadRow, addDeadRow, err := rata.NeedToScaleHypervisors(context.Background(), tc.AvailHypers, tc.Hypers)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			assert.Equal(tc.ExpectedRemoveDeadRow, removeDeadRow)
			assert.Equal(tc.ExpectedCreateHypervisor, create)
			assert.Equal(tc.ExpectedAddDeadRow, addDeadRow)
			assert.Equal(tc.ExpectedDestroyHypervisor, destroy)
		})
	}
}

func TestRataExtraOperations(t *testing.T) {
	assert := assert.New(t)

	cases := map[string]struct {
		PrepareAPI  func(*apiMock.Client)
		Hypers      []*isardvdi.OrchestratorHypervisor
		HyperMinCPU int
		HyperMinRAM int
		HyperMaxRAM int
		ExpectedErr string
	}{
		"if there are enough resources, it shouldn't do anything": {
			PrepareAPI: func(c *apiMock.Client) {},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:     "first",
				Status: isardvdi.HypervisorStatusOffline,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:     "second",
				Status: isardvdi.HypervisorStatusOnline,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 60,
				},
			}},
			HyperMinRAM: 50,
		},
		"if there's not enough RAM, it should set the hypervisor to only forced": {
			PrepareAPI: func(c *apiMock.Client) {
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("context.backgroundCtx"), "second", true).Return(nil)
			},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "first",
				Status:              isardvdi.HypervisorStatusOffline,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:                  "second",
				Status:              isardvdi.HypervisorStatusOnline,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 30,
				},
			}},
			HyperMinRAM: 50,
		},
		"if there's too much free RAM, it should remove the hypervisor from only forced": {
			PrepareAPI: func(c *apiMock.Client) {
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("context.backgroundCtx"), "second", false).Return(nil)
			},
			Hypers: []*isardvdi.OrchestratorHypervisor{{
				ID:                  "first",
				Status:              isardvdi.HypervisorStatusOffline,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 10,
				},
			}, {
				ID:                  "second",
				OnlyForced:          true,
				Status:              isardvdi.HypervisorStatusOnline,
				OrchestratorManaged: true,
				RAM: isardvdi.OrchestratorResourceLoad{
					Free: 200,
				},
			}},
			HyperMinRAM: 30,
			HyperMaxRAM: 150,
		},
		"regresssion test #1": {
			PrepareAPI: func(c *apiMock.Client) {
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("context.backgroundCtx"), "bm-e2-03", true).Return(nil)
				c.Mock.On("AdminHypervisorOnlyForced", mock.AnythingOfType("context.backgroundCtx"), "bm-e2-01", true).Return(nil)
			},
			Hypers: []*isardvdi.OrchestratorHypervisor{
				{
					ID:                  "bm-e4-02",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     39,
					MinFreeMemGB:        190,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  7,
						Free:  93,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 2051961,
						Used:  249909,
						Free:  1802051,
					},
				},
				{
					ID:                  "bm-e4-01",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					DestroyTime:         time.Now(),
					OrchestratorManaged: true,
					DesktopsStarted:     266,
					MinFreeMemGB:        190,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  23,
						Free:  77,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 2051961,
						Used:  1540080,
						Free:  511881,
					},
				},
				{
					ID:                  "bm-e2-03",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     70,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  30,
						Free:  70,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  407554,
						Free:  108300,
					},
				},
				{
					ID:                  "bm-e2-01",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     77,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  27,
						Free:  73,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  409618,
						Free:  106237,
					},
				},
				{
					ID:                  "bm-e2-02",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: false,
					DesktopsStarted:     64,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  25,
						Free:  75,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  441597,
						Free:  74258,
					},
				},
			},
			HyperMinRAM: 92160,
			HyperMaxRAM: 153600,
		},
		"regression test #2": {
			PrepareAPI: func(c *apiMock.Client) {},
			Hypers: []*isardvdi.OrchestratorHypervisor{
				{
					ID:                  "bm-e4-02",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     39,
					MinFreeMemGB:        190,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  7,
						Free:  93,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 2051961,
						Used:  249909,
						Free:  1802051,
					},
				},
				{
					ID:                  "bm-e4-01",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					DestroyTime:         time.Now(),
					OrchestratorManaged: true,
					DesktopsStarted:     266,
					MinFreeMemGB:        190,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  23,
						Free:  77,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 2051961,
						Used:  1540080,
						Free:  511881,
					},
				},
				{
					ID:                  "bm-e2-03",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          true,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     70,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  30,
						Free:  70,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  407554,
						Free:  108300,
					},
				},
				{
					ID:                  "bm-e2-01",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          true,
					Buffering:           false,
					OrchestratorManaged: true,
					DesktopsStarted:     77,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  27,
						Free:  73,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  409618,
						Free:  106237,
					},
				},
				{
					ID:                  "bm-e2-02",
					Status:              isardvdi.HypervisorStatusOnline,
					OnlyForced:          false,
					Buffering:           false,
					OrchestratorManaged: false,
					DesktopsStarted:     64,
					MinFreeMemGB:        47,
					CPU: isardvdi.OrchestratorResourceLoad{
						Total: 100,
						Used:  25,
						Free:  75,
					},
					RAM: isardvdi.OrchestratorResourceLoad{
						Total: 515855,
						Used:  441597,
						Free:  74258,
					},
				},
			},
			HyperMinRAM: 92160,
			HyperMaxRAM: 153600,
		},
	}

	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			log := zerolog.New(os.Stdout)
			api := &apiMock.Client{}

			tc.PrepareAPI(api)

			rata := director.NewRata(cfg.DirectorRata{
				HyperMinCPU: tc.HyperMinCPU,
				HyperMinRAM: tc.HyperMinRAM,
				HyperMaxRAM: tc.HyperMaxRAM,
			}, false, &log, api)

			err := rata.ExtraOperations(context.Background(), tc.Hypers)

			if tc.ExpectedErr != "" {
				assert.EqualError(err, tc.ExpectedErr)
			} else {
				assert.NoError(err)
			}

			api.AssertExpectations(t)
		})
	}
}
