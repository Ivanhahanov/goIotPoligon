package main

import (
	"context"
	device "github.com/Ivanhahanov/IotPoligon/deviceManagement/proto/device"
	"log"
	"net"

	"google.golang.org/grpc"
)

const (
	port = ":50051"
)

type server struct {
	device.UnimplementedGreeterServer
}

// SayHello implements helloworld.GreeterServer
func (s *server) SayHello(ctx context.Context, in *device.AddDeviceRequest) (*device.AddDeviceReply, error) {
	log.Printf("Received: %v", in.GetName())
	// TODO: check device description
	// TODO: save device description to database
	return &device.AddDeviceReply{Message: "Hello " + in.GetName()}, nil
}

func main() {
	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	s := grpc.NewServer()
	device.RegisterGreeterServer(s, &server{})
	if err := s.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
