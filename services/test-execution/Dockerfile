FROM golang:1.23-alpine AS builder

WORKDIR /app
ENV GOPROXY=https://goproxy.cn,direct

COPY go.mod ./

COPY . .

RUN go mod tidy
RUN go mod download

RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/server

FROM alpine:latest

WORKDIR /root/

COPY --from=builder /app/main .

EXPOSE 8083

CMD ["./main"]
