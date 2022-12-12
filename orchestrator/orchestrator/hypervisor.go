package orchestrator

import (
	"context"
	"errors"
	"fmt"
	"io"
	"time"

	"gitlab.com/isard/isardvdi-cli/pkg/client"
	"gitlab.com/isard/isardvdi/orchestrator/model"
	"gitlab.com/isard/isardvdi/pkg/db"
	operationsv1 "gitlab.com/isard/isardvdi/pkg/gen/proto/go/operations/v1"
)

func (o *Orchestrator) createHypervisor(ctx context.Context, req *operationsv1.CreateHypervisorRequest) {
	o.scaleMux.Lock()
	defer o.scaleMux.Unlock()

	o.wg.Add(1)
	defer o.wg.Done()

	o.scaling = true
	defer func() {
		o.scaling = false
	}()

	if err := o.openBufferingHypervisor(ctx); err != nil {
		o.log.Error().Err(err).Msg("open buffering hypervisors")
	}

	stream, err := o.operationsCli.CreateHypervisor(ctx, req)
	if err != nil {
		o.log.Error().Err(err).Msg("create hypervisor request stream")
		return
	}

	var id string
hyperCreate:
	for {
		select {
		case <-ctx.Done():
			o.log.Error().Str("id", id).Err(ErrTimeout).Msg("wait for the hypervisor to be created")
			return

		default:
			rsp, err := stream.Recv()
			if err != nil {
				if errors.Is(err, io.EOF) {
					break hyperCreate
				}

				o.log.Error().Str("id", id).Err(err).Msg("create hypervisor")
				return
			}

			id = rsp.Id

			if rsp.State == operationsv1.OperationState_OPERATION_STATE_FAILED {
				o.log.Error().Str("id", id).Err(errors.New(rsp.Msg)).Msg("create hypervisor failed")
				return
			}

			o.log.Debug().Str("id", id).Str("state", rsp.State.String()).Str("msg", rsp.Msg).Msg("create hypervisor update recieved")
		}
	}

	o.log.Debug().Str("id", id).Msg("hypervisor created")

	// Wait for the hypervisor to be online
	h := &model.Hypervisor{ID: id}
hyperOnline:
	for {
		select {
		case <-ctx.Done():
			o.log.Error().Str("id", id).Err(ErrTimeout).Msg("wait for the hypervisor to be online")
			return

		default:
			if err := h.Load(ctx, o.db); err != nil {
				if !errors.Is(err, db.ErrNotFound) {
					o.log.Error().Str("id", id).Str("status", string(h.Status)).Err(err).Msg("load hypervisor from DB")
					return
				}

			} else {
				if h.Status == client.HypervisorStatusOnline {
					break hyperOnline
				}
			}

			time.Sleep(time.Second)
		}
	}

	o.log.Debug().Str("id", id).Msg("hypervisor online")

	// TODO: IsardVDI Check

	// If it's only forced, disable it
	if h.OnlyForced {
		if err := o.apiCli.AdminHypervisorOnlyForced(ctx, id, false); err != nil {
			o.log.Error().Str("id", id).Str("status", string(h.Status)).Err(err).Msg("disable hypervisor only_forced")
			return
		}
	}

	if err := o.closeBufferingHypervisor(ctx); err != nil {
		o.log.Error().Err(err).Msg("close buffering hypervisors")
	}

	o.log.Info().Str("id", id).Msg("hypervisor started")
}

func (o *Orchestrator) destroyHypervisor(ctx context.Context, req *operationsv1.DestroyHypervisorRequest) {
	o.scaleMux.Lock()
	defer o.scaleMux.Unlock()

	o.wg.Add(1)
	defer o.wg.Done()

	o.scaling = true
	defer func() {
		o.scaling = false
	}()

	stream, err := o.operationsCli.DestroyHypervisor(ctx, req)
	if err != nil {
		o.log.Error().Str("id", req.Id).Err(err).Msg("destroy hypervisor request stream")
		return
	}

	for {
		rsp, err := stream.Recv()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}

			o.log.Error().Str("id", req.Id).Err(err).Msg("destroy hypervisor")
			return
		}

		o.log.Debug().Str("id", req.Id).Str("state", rsp.State.String()).Str("msg", rsp.Msg).Msg("destroy hypervisor update recieved")
	}

	o.log.Info().Str("id", req.Id).Msg("hypervisor destroyed")
}

func (o *Orchestrator) bufferingHypervisorOperation(ctx context.Context, onlyForced bool) error {
	hypers, err := o.apiCli.HypervisorList(ctx)
	if err != nil {
		return fmt.Errorf("list hypervisors: %w", err)
	}

	for _, h := range hypers {
		if client.GetBool(h.Buffering) && client.GetBool(h.OnlyForced) != onlyForced {
			if err := o.apiCli.AdminHypervisorOnlyForced(ctx, client.GetString(h.ID), onlyForced); err != nil {
				return fmt.Errorf("set hypervisor only forced state '%t': %w", onlyForced, err)
			}
		}
	}

	return nil
}

func (o *Orchestrator) openBufferingHypervisor(ctx context.Context) error {
	if err := o.bufferingHypervisorOperation(ctx, false); err != nil {
		return fmt.Errorf("open buffering hypervisor: %w", err)
	}

	return nil
}

func (o *Orchestrator) closeBufferingHypervisor(ctx context.Context) error {
	if err := o.bufferingHypervisorOperation(ctx, true); err != nil {
		return fmt.Errorf("close buffering hypervisor: %w", err)
	}

	return nil
}
