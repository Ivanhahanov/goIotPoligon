FROM golang:alpine as builder

RUN apk --no-cache add git

WORKDIR /app/deviceManagement
RUN GO111MODULE=on GOBIN=/usr/local/bin go get \
  github.com/bufbuild/buf/cmd/buf \
  github.com/bufbuild/buf/cmd/protoc-gen-buf-breaking \
  github.com/bufbuild/buf/cmd/protoc-gen-buf-lint \
  github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway \
  github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2 \
  google.golang.org/protobuf/cmd/protoc-gen-go \
  google.golang.org/grpc/cmd/protoc-gen-go-grpc

COPY . .
RUN go mod init github.com/Ivanhahanov/IotPoligon/deviceManagement
RUN go mod tidy
RUN go mod download
RUN buf beta mod update
RUN buf generate
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o deviceManagement

FROM alpine:latest
RUN mkdir /app
WORKDIR /app
COPY --from=builder /app/deviceManagement .

CMD ["./deviceManagement"]