// Code generated by protoc-gen-go. DO NOT EDIT.
// versions:
// 	protoc-gen-go v1.28.1
// 	protoc        (unknown)
// source: operations/v1/operations.proto

package operationsv1

import (
	protoreflect "google.golang.org/protobuf/reflect/protoreflect"
	protoimpl "google.golang.org/protobuf/runtime/protoimpl"
	reflect "reflect"
	sync "sync"
)

const (
	// Verify that this generated code is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(20 - protoimpl.MinVersion)
	// Verify that runtime/protoimpl is sufficiently up-to-date.
	_ = protoimpl.EnforceVersion(protoimpl.MaxVersion - 20)
)

// OperationState are the different states that a operation can be
type OperationState int32

const (
	// default zero value
	OperationState_OPERATION_STATE_UNSPECIFIED OperationState = 0
	// OPERATION_STATE_SCHEDULED means that the operation is queued, and it's going to be ran when it's its time
	OperationState_OPERATION_STATE_SCHEDULED OperationState = 1
	// OPERATION_STATE_ACTIVE means that the operation is being executed
	OperationState_OPERATION_STATE_ACTIVE OperationState = 2
	// OPERATION_STATE_FAILED means the operation has failed
	OperationState_OPERATION_STATE_FAILED OperationState = 3
	// OPERATION_STATE_COMPLETED means the operation has finished successfully
	OperationState_OPERATION_STATE_COMPLETED OperationState = 4
)

// Enum value maps for OperationState.
var (
	OperationState_name = map[int32]string{
		0: "OPERATION_STATE_UNSPECIFIED",
		1: "OPERATION_STATE_SCHEDULED",
		2: "OPERATION_STATE_ACTIVE",
		3: "OPERATION_STATE_FAILED",
		4: "OPERATION_STATE_COMPLETED",
	}
	OperationState_value = map[string]int32{
		"OPERATION_STATE_UNSPECIFIED": 0,
		"OPERATION_STATE_SCHEDULED":   1,
		"OPERATION_STATE_ACTIVE":      2,
		"OPERATION_STATE_FAILED":      3,
		"OPERATION_STATE_COMPLETED":   4,
	}
)

func (x OperationState) Enum() *OperationState {
	p := new(OperationState)
	*p = x
	return p
}

func (x OperationState) String() string {
	return protoimpl.X.EnumStringOf(x.Descriptor(), protoreflect.EnumNumber(x))
}

func (OperationState) Descriptor() protoreflect.EnumDescriptor {
	return file_operations_v1_operations_proto_enumTypes[0].Descriptor()
}

func (OperationState) Type() protoreflect.EnumType {
	return &file_operations_v1_operations_proto_enumTypes[0]
}

func (x OperationState) Number() protoreflect.EnumNumber {
	return protoreflect.EnumNumber(x)
}

// Deprecated: Use OperationState.Descriptor instead.
func (OperationState) EnumDescriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{0}
}

// HypervisorCapabilites are the different capabilites that a hypervisor can have
type HypervisorCapabilities int32

const (
	// default zero value
	HypervisorCapabilities_HYPERVISOR_CAPABILITIES_UNSPECIFIED HypervisorCapabilities = 0
	// HYPERVISOR_CAPABILITIES_STORAGE means the hypervisor has access to the shared storage pool
	HypervisorCapabilities_HYPERVISOR_CAPABILITIES_STORAGE HypervisorCapabilities = 1
	// HYPERVISOR_CAPABILITIES_GPU means the hypervisor has access to a GPU
	HypervisorCapabilities_HYPERVISOR_CAPABILITIES_GPU HypervisorCapabilities = 2
)

// Enum value maps for HypervisorCapabilities.
var (
	HypervisorCapabilities_name = map[int32]string{
		0: "HYPERVISOR_CAPABILITIES_UNSPECIFIED",
		1: "HYPERVISOR_CAPABILITIES_STORAGE",
		2: "HYPERVISOR_CAPABILITIES_GPU",
	}
	HypervisorCapabilities_value = map[string]int32{
		"HYPERVISOR_CAPABILITIES_UNSPECIFIED": 0,
		"HYPERVISOR_CAPABILITIES_STORAGE":     1,
		"HYPERVISOR_CAPABILITIES_GPU":         2,
	}
)

func (x HypervisorCapabilities) Enum() *HypervisorCapabilities {
	p := new(HypervisorCapabilities)
	*p = x
	return p
}

func (x HypervisorCapabilities) String() string {
	return protoimpl.X.EnumStringOf(x.Descriptor(), protoreflect.EnumNumber(x))
}

func (HypervisorCapabilities) Descriptor() protoreflect.EnumDescriptor {
	return file_operations_v1_operations_proto_enumTypes[1].Descriptor()
}

func (HypervisorCapabilities) Type() protoreflect.EnumType {
	return &file_operations_v1_operations_proto_enumTypes[1]
}

func (x HypervisorCapabilities) Number() protoreflect.EnumNumber {
	return protoreflect.EnumNumber(x)
}

// Deprecated: Use HypervisorCapabilities.Descriptor instead.
func (HypervisorCapabilities) EnumDescriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{1}
}

// CreateHypervisorRequest is the request for the CreateHypervisor method
type CreateHypervisorRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// min_cpu is the minimum number of CPU threads that the machine has to have
	MinCpu int32 `protobuf:"varint,1,opt,name=min_cpu,json=minCpu,proto3" json:"min_cpu,omitempty"`
	// min_ram is the minimum number of RAM that the machine has to have. It's in MB
	MinRam int32 `protobuf:"varint,2,opt,name=min_ram,json=minRam,proto3" json:"min_ram,omitempty"`
	// capabilities are the capabilities that the hypervisor has to have
	Capabilities []HypervisorCapabilities `protobuf:"varint,3,rep,packed,name=capabilities,proto3,enum=operations.v1.HypervisorCapabilities" json:"capabilities,omitempty"`
}

func (x *CreateHypervisorRequest) Reset() {
	*x = CreateHypervisorRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[0]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *CreateHypervisorRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateHypervisorRequest) ProtoMessage() {}

func (x *CreateHypervisorRequest) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[0]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use CreateHypervisorRequest.ProtoReflect.Descriptor instead.
func (*CreateHypervisorRequest) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{0}
}

func (x *CreateHypervisorRequest) GetMinCpu() int32 {
	if x != nil {
		return x.MinCpu
	}
	return 0
}

func (x *CreateHypervisorRequest) GetMinRam() int32 {
	if x != nil {
		return x.MinRam
	}
	return 0
}

func (x *CreateHypervisorRequest) GetCapabilities() []HypervisorCapabilities {
	if x != nil {
		return x.Capabilities
	}
	return nil
}

// CreateHypervisorResponse is the response for the CreateHypervisor method
type CreateHypervisorResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// id is the generated ID of the hypervisor
	Id string `protobuf:"bytes,1,opt,name=id,proto3" json:"id,omitempty"`
	// state is the state of the operation
	State OperationState `protobuf:"varint,2,opt,name=state,proto3,enum=operations.v1.OperationState" json:"state,omitempty"`
	// msg contains info related with the operation
	Msg string `protobuf:"bytes,3,opt,name=msg,proto3" json:"msg,omitempty"`
}

func (x *CreateHypervisorResponse) Reset() {
	*x = CreateHypervisorResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[1]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *CreateHypervisorResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateHypervisorResponse) ProtoMessage() {}

func (x *CreateHypervisorResponse) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[1]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use CreateHypervisorResponse.ProtoReflect.Descriptor instead.
func (*CreateHypervisorResponse) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{1}
}

func (x *CreateHypervisorResponse) GetId() string {
	if x != nil {
		return x.Id
	}
	return ""
}

func (x *CreateHypervisorResponse) GetState() OperationState {
	if x != nil {
		return x.State
	}
	return OperationState_OPERATION_STATE_UNSPECIFIED
}

func (x *CreateHypervisorResponse) GetMsg() string {
	if x != nil {
		return x.Msg
	}
	return ""
}

// DestroyHypervisorRequest is the request for the DestroyHypervisor method
type DestroyHypervisorRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// id is the ID of the hypervisor
	Id string `protobuf:"bytes,1,opt,name=id,proto3" json:"id,omitempty"`
}

func (x *DestroyHypervisorRequest) Reset() {
	*x = DestroyHypervisorRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[2]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *DestroyHypervisorRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*DestroyHypervisorRequest) ProtoMessage() {}

func (x *DestroyHypervisorRequest) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[2]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use DestroyHypervisorRequest.ProtoReflect.Descriptor instead.
func (*DestroyHypervisorRequest) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{2}
}

func (x *DestroyHypervisorRequest) GetId() string {
	if x != nil {
		return x.Id
	}
	return ""
}

// DestroyHypervisorResponse is the response for the DestroyHypervisor method
type DestroyHypervisorResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// state is the state of the operation
	State OperationState `protobuf:"varint,1,opt,name=state,proto3,enum=operations.v1.OperationState" json:"state,omitempty"`
	// msg contains info related with the operation
	Msg string `protobuf:"bytes,2,opt,name=msg,proto3" json:"msg,omitempty"`
}

func (x *DestroyHypervisorResponse) Reset() {
	*x = DestroyHypervisorResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[3]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *DestroyHypervisorResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*DestroyHypervisorResponse) ProtoMessage() {}

func (x *DestroyHypervisorResponse) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[3]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use DestroyHypervisorResponse.ProtoReflect.Descriptor instead.
func (*DestroyHypervisorResponse) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{3}
}

func (x *DestroyHypervisorResponse) GetState() OperationState {
	if x != nil {
		return x.State
	}
	return OperationState_OPERATION_STATE_UNSPECIFIED
}

func (x *DestroyHypervisorResponse) GetMsg() string {
	if x != nil {
		return x.Msg
	}
	return ""
}

// ExpandStorageRequest is the request for the ExpandStorage method
type ExpandStorageRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// min_bytes is the minimum number of bytes that the storage needs to be expanded
	MinBytes int32 `protobuf:"varint,1,opt,name=min_bytes,json=minBytes,proto3" json:"min_bytes,omitempty"`
}

func (x *ExpandStorageRequest) Reset() {
	*x = ExpandStorageRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[4]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ExpandStorageRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ExpandStorageRequest) ProtoMessage() {}

func (x *ExpandStorageRequest) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[4]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ExpandStorageRequest.ProtoReflect.Descriptor instead.
func (*ExpandStorageRequest) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{4}
}

func (x *ExpandStorageRequest) GetMinBytes() int32 {
	if x != nil {
		return x.MinBytes
	}
	return 0
}

// ExpandStorageResponse is the response for the ExpandStorage method
type ExpandStorageResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// state is the state of the operation
	State OperationState `protobuf:"varint,1,opt,name=state,proto3,enum=operations.v1.OperationState" json:"state,omitempty"`
	// msg contains info related with the operation
	Msg string `protobuf:"bytes,2,opt,name=msg,proto3" json:"msg,omitempty"`
}

func (x *ExpandStorageResponse) Reset() {
	*x = ExpandStorageResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[5]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ExpandStorageResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ExpandStorageResponse) ProtoMessage() {}

func (x *ExpandStorageResponse) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[5]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ExpandStorageResponse.ProtoReflect.Descriptor instead.
func (*ExpandStorageResponse) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{5}
}

func (x *ExpandStorageResponse) GetState() OperationState {
	if x != nil {
		return x.State
	}
	return OperationState_OPERATION_STATE_UNSPECIFIED
}

func (x *ExpandStorageResponse) GetMsg() string {
	if x != nil {
		return x.Msg
	}
	return ""
}

// ShrinkStorageRequest is the request for the ShrinkStorage method
type ShrinkStorageRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// max_bytes is the maximum number of bytes that the storage needs to be shrink
	MaxBytes int32 `protobuf:"varint,1,opt,name=max_bytes,json=maxBytes,proto3" json:"max_bytes,omitempty"`
}

func (x *ShrinkStorageRequest) Reset() {
	*x = ShrinkStorageRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[6]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ShrinkStorageRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ShrinkStorageRequest) ProtoMessage() {}

func (x *ShrinkStorageRequest) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[6]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ShrinkStorageRequest.ProtoReflect.Descriptor instead.
func (*ShrinkStorageRequest) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{6}
}

func (x *ShrinkStorageRequest) GetMaxBytes() int32 {
	if x != nil {
		return x.MaxBytes
	}
	return 0
}

// ShrinkStorageResponse is the response for the ShrinkStorage method
type ShrinkStorageResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// state is the state of the operation
	State OperationState `protobuf:"varint,1,opt,name=state,proto3,enum=operations.v1.OperationState" json:"state,omitempty"`
	// msg contains info related with the operation
	Msg string `protobuf:"bytes,2,opt,name=msg,proto3" json:"msg,omitempty"`
}

func (x *ShrinkStorageResponse) Reset() {
	*x = ShrinkStorageResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[7]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *ShrinkStorageResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*ShrinkStorageResponse) ProtoMessage() {}

func (x *ShrinkStorageResponse) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[7]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use ShrinkStorageResponse.ProtoReflect.Descriptor instead.
func (*ShrinkStorageResponse) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{7}
}

func (x *ShrinkStorageResponse) GetState() OperationState {
	if x != nil {
		return x.State
	}
	return OperationState_OPERATION_STATE_UNSPECIFIED
}

func (x *ShrinkStorageResponse) GetMsg() string {
	if x != nil {
		return x.Msg
	}
	return ""
}

// CreateBackupRequest is the request for the CreateBackup method
type CreateBackupRequest struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields
}

func (x *CreateBackupRequest) Reset() {
	*x = CreateBackupRequest{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[8]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *CreateBackupRequest) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateBackupRequest) ProtoMessage() {}

func (x *CreateBackupRequest) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[8]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use CreateBackupRequest.ProtoReflect.Descriptor instead.
func (*CreateBackupRequest) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{8}
}

// CreateBackupResponse is the response for the CreateBackup method
type CreateBackupResponse struct {
	state         protoimpl.MessageState
	sizeCache     protoimpl.SizeCache
	unknownFields protoimpl.UnknownFields

	// state is the state of the operation
	State OperationState `protobuf:"varint,1,opt,name=state,proto3,enum=operations.v1.OperationState" json:"state,omitempty"`
	// msg contains info related with the operation
	Msg string `protobuf:"bytes,2,opt,name=msg,proto3" json:"msg,omitempty"`
}

func (x *CreateBackupResponse) Reset() {
	*x = CreateBackupResponse{}
	if protoimpl.UnsafeEnabled {
		mi := &file_operations_v1_operations_proto_msgTypes[9]
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		ms.StoreMessageInfo(mi)
	}
}

func (x *CreateBackupResponse) String() string {
	return protoimpl.X.MessageStringOf(x)
}

func (*CreateBackupResponse) ProtoMessage() {}

func (x *CreateBackupResponse) ProtoReflect() protoreflect.Message {
	mi := &file_operations_v1_operations_proto_msgTypes[9]
	if protoimpl.UnsafeEnabled && x != nil {
		ms := protoimpl.X.MessageStateOf(protoimpl.Pointer(x))
		if ms.LoadMessageInfo() == nil {
			ms.StoreMessageInfo(mi)
		}
		return ms
	}
	return mi.MessageOf(x)
}

// Deprecated: Use CreateBackupResponse.ProtoReflect.Descriptor instead.
func (*CreateBackupResponse) Descriptor() ([]byte, []int) {
	return file_operations_v1_operations_proto_rawDescGZIP(), []int{9}
}

func (x *CreateBackupResponse) GetState() OperationState {
	if x != nil {
		return x.State
	}
	return OperationState_OPERATION_STATE_UNSPECIFIED
}

func (x *CreateBackupResponse) GetMsg() string {
	if x != nil {
		return x.Msg
	}
	return ""
}

var File_operations_v1_operations_proto protoreflect.FileDescriptor

var file_operations_v1_operations_proto_rawDesc = []byte{
	0x0a, 0x1e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2f, 0x76, 0x31, 0x2f,
	0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x70, 0x72, 0x6f, 0x74, 0x6f,
	0x12, 0x0d, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x22,
	0x96, 0x01, 0x0a, 0x17, 0x43, 0x72, 0x65, 0x61, 0x74, 0x65, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76,
	0x69, 0x73, 0x6f, 0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x17, 0x0a, 0x07, 0x6d,
	0x69, 0x6e, 0x5f, 0x63, 0x70, 0x75, 0x18, 0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x06, 0x6d, 0x69,
	0x6e, 0x43, 0x70, 0x75, 0x12, 0x17, 0x0a, 0x07, 0x6d, 0x69, 0x6e, 0x5f, 0x72, 0x61, 0x6d, 0x18,
	0x02, 0x20, 0x01, 0x28, 0x05, 0x52, 0x06, 0x6d, 0x69, 0x6e, 0x52, 0x61, 0x6d, 0x12, 0x49, 0x0a,
	0x0c, 0x63, 0x61, 0x70, 0x61, 0x62, 0x69, 0x6c, 0x69, 0x74, 0x69, 0x65, 0x73, 0x18, 0x03, 0x20,
	0x03, 0x28, 0x0e, 0x32, 0x25, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73,
	0x2e, 0x76, 0x31, 0x2e, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x43, 0x61,
	0x70, 0x61, 0x62, 0x69, 0x6c, 0x69, 0x74, 0x69, 0x65, 0x73, 0x52, 0x0c, 0x63, 0x61, 0x70, 0x61,
	0x62, 0x69, 0x6c, 0x69, 0x74, 0x69, 0x65, 0x73, 0x22, 0x71, 0x0a, 0x18, 0x43, 0x72, 0x65, 0x61,
	0x74, 0x65, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x52, 0x65, 0x73, 0x70,
	0x6f, 0x6e, 0x73, 0x65, 0x12, 0x0e, 0x0a, 0x02, 0x69, 0x64, 0x18, 0x01, 0x20, 0x01, 0x28, 0x09,
	0x52, 0x02, 0x69, 0x64, 0x12, 0x33, 0x0a, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x18, 0x02, 0x20,
	0x01, 0x28, 0x0e, 0x32, 0x1d, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73,
	0x2e, 0x76, 0x31, 0x2e, 0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x53, 0x74, 0x61,
	0x74, 0x65, 0x52, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x12, 0x10, 0x0a, 0x03, 0x6d, 0x73, 0x67,
	0x18, 0x03, 0x20, 0x01, 0x28, 0x09, 0x52, 0x03, 0x6d, 0x73, 0x67, 0x22, 0x2a, 0x0a, 0x18, 0x44,
	0x65, 0x73, 0x74, 0x72, 0x6f, 0x79, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72,
	0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x0e, 0x0a, 0x02, 0x69, 0x64, 0x18, 0x01, 0x20,
	0x01, 0x28, 0x09, 0x52, 0x02, 0x69, 0x64, 0x22, 0x62, 0x0a, 0x19, 0x44, 0x65, 0x73, 0x74, 0x72,
	0x6f, 0x79, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x52, 0x65, 0x73, 0x70,
	0x6f, 0x6e, 0x73, 0x65, 0x12, 0x33, 0x0a, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x18, 0x01, 0x20,
	0x01, 0x28, 0x0e, 0x32, 0x1d, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73,
	0x2e, 0x76, 0x31, 0x2e, 0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x53, 0x74, 0x61,
	0x74, 0x65, 0x52, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x12, 0x10, 0x0a, 0x03, 0x6d, 0x73, 0x67,
	0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x03, 0x6d, 0x73, 0x67, 0x22, 0x33, 0x0a, 0x14, 0x45,
	0x78, 0x70, 0x61, 0x6e, 0x64, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65, 0x71, 0x75,
	0x65, 0x73, 0x74, 0x12, 0x1b, 0x0a, 0x09, 0x6d, 0x69, 0x6e, 0x5f, 0x62, 0x79, 0x74, 0x65, 0x73,
	0x18, 0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x08, 0x6d, 0x69, 0x6e, 0x42, 0x79, 0x74, 0x65, 0x73,
	0x22, 0x5e, 0x0a, 0x15, 0x45, 0x78, 0x70, 0x61, 0x6e, 0x64, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67,
	0x65, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x12, 0x33, 0x0a, 0x05, 0x73, 0x74, 0x61,
	0x74, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x0e, 0x32, 0x1d, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61,
	0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69,
	0x6f, 0x6e, 0x53, 0x74, 0x61, 0x74, 0x65, 0x52, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x12, 0x10,
	0x0a, 0x03, 0x6d, 0x73, 0x67, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x03, 0x6d, 0x73, 0x67,
	0x22, 0x33, 0x0a, 0x14, 0x53, 0x68, 0x72, 0x69, 0x6e, 0x6b, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67,
	0x65, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x12, 0x1b, 0x0a, 0x09, 0x6d, 0x61, 0x78, 0x5f,
	0x62, 0x79, 0x74, 0x65, 0x73, 0x18, 0x01, 0x20, 0x01, 0x28, 0x05, 0x52, 0x08, 0x6d, 0x61, 0x78,
	0x42, 0x79, 0x74, 0x65, 0x73, 0x22, 0x5e, 0x0a, 0x15, 0x53, 0x68, 0x72, 0x69, 0x6e, 0x6b, 0x53,
	0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x12, 0x33,
	0x0a, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x18, 0x01, 0x20, 0x01, 0x28, 0x0e, 0x32, 0x1d, 0x2e,
	0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x4f, 0x70,
	0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x53, 0x74, 0x61, 0x74, 0x65, 0x52, 0x05, 0x73, 0x74,
	0x61, 0x74, 0x65, 0x12, 0x10, 0x0a, 0x03, 0x6d, 0x73, 0x67, 0x18, 0x02, 0x20, 0x01, 0x28, 0x09,
	0x52, 0x03, 0x6d, 0x73, 0x67, 0x22, 0x15, 0x0a, 0x13, 0x43, 0x72, 0x65, 0x61, 0x74, 0x65, 0x42,
	0x61, 0x63, 0x6b, 0x75, 0x70, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x22, 0x5d, 0x0a, 0x14,
	0x43, 0x72, 0x65, 0x61, 0x74, 0x65, 0x42, 0x61, 0x63, 0x6b, 0x75, 0x70, 0x52, 0x65, 0x73, 0x70,
	0x6f, 0x6e, 0x73, 0x65, 0x12, 0x33, 0x0a, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x18, 0x01, 0x20,
	0x01, 0x28, 0x0e, 0x32, 0x1d, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73,
	0x2e, 0x76, 0x31, 0x2e, 0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x53, 0x74, 0x61,
	0x74, 0x65, 0x52, 0x05, 0x73, 0x74, 0x61, 0x74, 0x65, 0x12, 0x10, 0x0a, 0x03, 0x6d, 0x73, 0x67,
	0x18, 0x02, 0x20, 0x01, 0x28, 0x09, 0x52, 0x03, 0x6d, 0x73, 0x67, 0x2a, 0xa7, 0x01, 0x0a, 0x0e,
	0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x53, 0x74, 0x61, 0x74, 0x65, 0x12, 0x1f,
	0x0a, 0x1b, 0x4f, 0x50, 0x45, 0x52, 0x41, 0x54, 0x49, 0x4f, 0x4e, 0x5f, 0x53, 0x54, 0x41, 0x54,
	0x45, 0x5f, 0x55, 0x4e, 0x53, 0x50, 0x45, 0x43, 0x49, 0x46, 0x49, 0x45, 0x44, 0x10, 0x00, 0x12,
	0x1d, 0x0a, 0x19, 0x4f, 0x50, 0x45, 0x52, 0x41, 0x54, 0x49, 0x4f, 0x4e, 0x5f, 0x53, 0x54, 0x41,
	0x54, 0x45, 0x5f, 0x53, 0x43, 0x48, 0x45, 0x44, 0x55, 0x4c, 0x45, 0x44, 0x10, 0x01, 0x12, 0x1a,
	0x0a, 0x16, 0x4f, 0x50, 0x45, 0x52, 0x41, 0x54, 0x49, 0x4f, 0x4e, 0x5f, 0x53, 0x54, 0x41, 0x54,
	0x45, 0x5f, 0x41, 0x43, 0x54, 0x49, 0x56, 0x45, 0x10, 0x02, 0x12, 0x1a, 0x0a, 0x16, 0x4f, 0x50,
	0x45, 0x52, 0x41, 0x54, 0x49, 0x4f, 0x4e, 0x5f, 0x53, 0x54, 0x41, 0x54, 0x45, 0x5f, 0x46, 0x41,
	0x49, 0x4c, 0x45, 0x44, 0x10, 0x03, 0x12, 0x1d, 0x0a, 0x19, 0x4f, 0x50, 0x45, 0x52, 0x41, 0x54,
	0x49, 0x4f, 0x4e, 0x5f, 0x53, 0x54, 0x41, 0x54, 0x45, 0x5f, 0x43, 0x4f, 0x4d, 0x50, 0x4c, 0x45,
	0x54, 0x45, 0x44, 0x10, 0x04, 0x2a, 0x87, 0x01, 0x0a, 0x16, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76,
	0x69, 0x73, 0x6f, 0x72, 0x43, 0x61, 0x70, 0x61, 0x62, 0x69, 0x6c, 0x69, 0x74, 0x69, 0x65, 0x73,
	0x12, 0x27, 0x0a, 0x23, 0x48, 0x59, 0x50, 0x45, 0x52, 0x56, 0x49, 0x53, 0x4f, 0x52, 0x5f, 0x43,
	0x41, 0x50, 0x41, 0x42, 0x49, 0x4c, 0x49, 0x54, 0x49, 0x45, 0x53, 0x5f, 0x55, 0x4e, 0x53, 0x50,
	0x45, 0x43, 0x49, 0x46, 0x49, 0x45, 0x44, 0x10, 0x00, 0x12, 0x23, 0x0a, 0x1f, 0x48, 0x59, 0x50,
	0x45, 0x52, 0x56, 0x49, 0x53, 0x4f, 0x52, 0x5f, 0x43, 0x41, 0x50, 0x41, 0x42, 0x49, 0x4c, 0x49,
	0x54, 0x49, 0x45, 0x53, 0x5f, 0x53, 0x54, 0x4f, 0x52, 0x41, 0x47, 0x45, 0x10, 0x01, 0x12, 0x1f,
	0x0a, 0x1b, 0x48, 0x59, 0x50, 0x45, 0x52, 0x56, 0x49, 0x53, 0x4f, 0x52, 0x5f, 0x43, 0x41, 0x50,
	0x41, 0x42, 0x49, 0x4c, 0x49, 0x54, 0x49, 0x45, 0x53, 0x5f, 0x47, 0x50, 0x55, 0x10, 0x02, 0x32,
	0x85, 0x04, 0x0a, 0x11, 0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x53, 0x65,
	0x72, 0x76, 0x69, 0x63, 0x65, 0x12, 0x67, 0x0a, 0x10, 0x43, 0x72, 0x65, 0x61, 0x74, 0x65, 0x48,
	0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x12, 0x26, 0x2e, 0x6f, 0x70, 0x65, 0x72,
	0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x43, 0x72, 0x65, 0x61, 0x74, 0x65,
	0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73,
	0x74, 0x1a, 0x27, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76,
	0x31, 0x2e, 0x43, 0x72, 0x65, 0x61, 0x74, 0x65, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73,
	0x6f, 0x72, 0x52, 0x65, 0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x22, 0x00, 0x30, 0x01, 0x12, 0x6a,
	0x0a, 0x11, 0x44, 0x65, 0x73, 0x74, 0x72, 0x6f, 0x79, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69,
	0x73, 0x6f, 0x72, 0x12, 0x27, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73,
	0x2e, 0x76, 0x31, 0x2e, 0x44, 0x65, 0x73, 0x74, 0x72, 0x6f, 0x79, 0x48, 0x79, 0x70, 0x65, 0x72,
	0x76, 0x69, 0x73, 0x6f, 0x72, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x28, 0x2e, 0x6f,
	0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x44, 0x65, 0x73,
	0x74, 0x72, 0x6f, 0x79, 0x48, 0x79, 0x70, 0x65, 0x72, 0x76, 0x69, 0x73, 0x6f, 0x72, 0x52, 0x65,
	0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x22, 0x00, 0x30, 0x01, 0x12, 0x5e, 0x0a, 0x0d, 0x45, 0x78,
	0x70, 0x61, 0x6e, 0x64, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x12, 0x23, 0x2e, 0x6f, 0x70,
	0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x45, 0x78, 0x70, 0x61,
	0x6e, 0x64, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74,
	0x1a, 0x24, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31,
	0x2e, 0x45, 0x78, 0x70, 0x61, 0x6e, 0x64, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65,
	0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x22, 0x00, 0x30, 0x01, 0x12, 0x5e, 0x0a, 0x0d, 0x53, 0x68,
	0x72, 0x69, 0x6e, 0x6b, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x12, 0x23, 0x2e, 0x6f, 0x70,
	0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x53, 0x68, 0x72, 0x69,
	0x6e, 0x6b, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74,
	0x1a, 0x24, 0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31,
	0x2e, 0x53, 0x68, 0x72, 0x69, 0x6e, 0x6b, 0x53, 0x74, 0x6f, 0x72, 0x61, 0x67, 0x65, 0x52, 0x65,
	0x73, 0x70, 0x6f, 0x6e, 0x73, 0x65, 0x22, 0x00, 0x30, 0x01, 0x12, 0x5b, 0x0a, 0x0c, 0x43, 0x72,
	0x65, 0x61, 0x74, 0x65, 0x42, 0x61, 0x63, 0x6b, 0x75, 0x70, 0x12, 0x22, 0x2e, 0x6f, 0x70, 0x65,
	0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x43, 0x72, 0x65, 0x61, 0x74,
	0x65, 0x42, 0x61, 0x63, 0x6b, 0x75, 0x70, 0x52, 0x65, 0x71, 0x75, 0x65, 0x73, 0x74, 0x1a, 0x23,
	0x2e, 0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x2e, 0x43,
	0x72, 0x65, 0x61, 0x74, 0x65, 0x42, 0x61, 0x63, 0x6b, 0x75, 0x70, 0x52, 0x65, 0x73, 0x70, 0x6f,
	0x6e, 0x73, 0x65, 0x22, 0x00, 0x30, 0x01, 0x42, 0xc0, 0x01, 0x0a, 0x11, 0x63, 0x6f, 0x6d, 0x2e,
	0x6f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x76, 0x31, 0x42, 0x0f, 0x4f,
	0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x50, 0x72, 0x6f, 0x74, 0x6f, 0x50, 0x01,
	0x5a, 0x45, 0x67, 0x69, 0x74, 0x6c, 0x61, 0x62, 0x2e, 0x63, 0x6f, 0x6d, 0x2f, 0x69, 0x73, 0x61,
	0x72, 0x64, 0x2f, 0x69, 0x73, 0x61, 0x72, 0x64, 0x76, 0x64, 0x69, 0x2f, 0x70, 0x6b, 0x67, 0x2f,
	0x67, 0x65, 0x6e, 0x2f, 0x70, 0x72, 0x6f, 0x74, 0x6f, 0x2f, 0x67, 0x6f, 0x2f, 0x6f, 0x70, 0x65,
	0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2f, 0x76, 0x31, 0x3b, 0x6f, 0x70, 0x65, 0x72, 0x61,
	0x74, 0x69, 0x6f, 0x6e, 0x73, 0x76, 0x31, 0xa2, 0x02, 0x03, 0x4f, 0x58, 0x58, 0xaa, 0x02, 0x0d,
	0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x2e, 0x56, 0x31, 0xca, 0x02, 0x0d,
	0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x5c, 0x56, 0x31, 0xe2, 0x02, 0x19,
	0x4f, 0x70, 0x65, 0x72, 0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x5c, 0x56, 0x31, 0x5c, 0x47, 0x50,
	0x42, 0x4d, 0x65, 0x74, 0x61, 0x64, 0x61, 0x74, 0x61, 0xea, 0x02, 0x0e, 0x4f, 0x70, 0x65, 0x72,
	0x61, 0x74, 0x69, 0x6f, 0x6e, 0x73, 0x3a, 0x3a, 0x56, 0x31, 0x62, 0x06, 0x70, 0x72, 0x6f, 0x74,
	0x6f, 0x33,
}

var (
	file_operations_v1_operations_proto_rawDescOnce sync.Once
	file_operations_v1_operations_proto_rawDescData = file_operations_v1_operations_proto_rawDesc
)

func file_operations_v1_operations_proto_rawDescGZIP() []byte {
	file_operations_v1_operations_proto_rawDescOnce.Do(func() {
		file_operations_v1_operations_proto_rawDescData = protoimpl.X.CompressGZIP(file_operations_v1_operations_proto_rawDescData)
	})
	return file_operations_v1_operations_proto_rawDescData
}

var file_operations_v1_operations_proto_enumTypes = make([]protoimpl.EnumInfo, 2)
var file_operations_v1_operations_proto_msgTypes = make([]protoimpl.MessageInfo, 10)
var file_operations_v1_operations_proto_goTypes = []interface{}{
	(OperationState)(0),               // 0: operations.v1.OperationState
	(HypervisorCapabilities)(0),       // 1: operations.v1.HypervisorCapabilities
	(*CreateHypervisorRequest)(nil),   // 2: operations.v1.CreateHypervisorRequest
	(*CreateHypervisorResponse)(nil),  // 3: operations.v1.CreateHypervisorResponse
	(*DestroyHypervisorRequest)(nil),  // 4: operations.v1.DestroyHypervisorRequest
	(*DestroyHypervisorResponse)(nil), // 5: operations.v1.DestroyHypervisorResponse
	(*ExpandStorageRequest)(nil),      // 6: operations.v1.ExpandStorageRequest
	(*ExpandStorageResponse)(nil),     // 7: operations.v1.ExpandStorageResponse
	(*ShrinkStorageRequest)(nil),      // 8: operations.v1.ShrinkStorageRequest
	(*ShrinkStorageResponse)(nil),     // 9: operations.v1.ShrinkStorageResponse
	(*CreateBackupRequest)(nil),       // 10: operations.v1.CreateBackupRequest
	(*CreateBackupResponse)(nil),      // 11: operations.v1.CreateBackupResponse
}
var file_operations_v1_operations_proto_depIdxs = []int32{
	1,  // 0: operations.v1.CreateHypervisorRequest.capabilities:type_name -> operations.v1.HypervisorCapabilities
	0,  // 1: operations.v1.CreateHypervisorResponse.state:type_name -> operations.v1.OperationState
	0,  // 2: operations.v1.DestroyHypervisorResponse.state:type_name -> operations.v1.OperationState
	0,  // 3: operations.v1.ExpandStorageResponse.state:type_name -> operations.v1.OperationState
	0,  // 4: operations.v1.ShrinkStorageResponse.state:type_name -> operations.v1.OperationState
	0,  // 5: operations.v1.CreateBackupResponse.state:type_name -> operations.v1.OperationState
	2,  // 6: operations.v1.OperationsService.CreateHypervisor:input_type -> operations.v1.CreateHypervisorRequest
	4,  // 7: operations.v1.OperationsService.DestroyHypervisor:input_type -> operations.v1.DestroyHypervisorRequest
	6,  // 8: operations.v1.OperationsService.ExpandStorage:input_type -> operations.v1.ExpandStorageRequest
	8,  // 9: operations.v1.OperationsService.ShrinkStorage:input_type -> operations.v1.ShrinkStorageRequest
	10, // 10: operations.v1.OperationsService.CreateBackup:input_type -> operations.v1.CreateBackupRequest
	3,  // 11: operations.v1.OperationsService.CreateHypervisor:output_type -> operations.v1.CreateHypervisorResponse
	5,  // 12: operations.v1.OperationsService.DestroyHypervisor:output_type -> operations.v1.DestroyHypervisorResponse
	7,  // 13: operations.v1.OperationsService.ExpandStorage:output_type -> operations.v1.ExpandStorageResponse
	9,  // 14: operations.v1.OperationsService.ShrinkStorage:output_type -> operations.v1.ShrinkStorageResponse
	11, // 15: operations.v1.OperationsService.CreateBackup:output_type -> operations.v1.CreateBackupResponse
	11, // [11:16] is the sub-list for method output_type
	6,  // [6:11] is the sub-list for method input_type
	6,  // [6:6] is the sub-list for extension type_name
	6,  // [6:6] is the sub-list for extension extendee
	0,  // [0:6] is the sub-list for field type_name
}

func init() { file_operations_v1_operations_proto_init() }
func file_operations_v1_operations_proto_init() {
	if File_operations_v1_operations_proto != nil {
		return
	}
	if !protoimpl.UnsafeEnabled {
		file_operations_v1_operations_proto_msgTypes[0].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*CreateHypervisorRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[1].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*CreateHypervisorResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[2].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*DestroyHypervisorRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[3].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*DestroyHypervisorResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[4].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ExpandStorageRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[5].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ExpandStorageResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[6].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ShrinkStorageRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[7].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*ShrinkStorageResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[8].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*CreateBackupRequest); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
		file_operations_v1_operations_proto_msgTypes[9].Exporter = func(v interface{}, i int) interface{} {
			switch v := v.(*CreateBackupResponse); i {
			case 0:
				return &v.state
			case 1:
				return &v.sizeCache
			case 2:
				return &v.unknownFields
			default:
				return nil
			}
		}
	}
	type x struct{}
	out := protoimpl.TypeBuilder{
		File: protoimpl.DescBuilder{
			GoPackagePath: reflect.TypeOf(x{}).PkgPath(),
			RawDescriptor: file_operations_v1_operations_proto_rawDesc,
			NumEnums:      2,
			NumMessages:   10,
			NumExtensions: 0,
			NumServices:   1,
		},
		GoTypes:           file_operations_v1_operations_proto_goTypes,
		DependencyIndexes: file_operations_v1_operations_proto_depIdxs,
		EnumInfos:         file_operations_v1_operations_proto_enumTypes,
		MessageInfos:      file_operations_v1_operations_proto_msgTypes,
	}.Build()
	File_operations_v1_operations_proto = out.File
	file_operations_v1_operations_proto_rawDesc = nil
	file_operations_v1_operations_proto_goTypes = nil
	file_operations_v1_operations_proto_depIdxs = nil
}
