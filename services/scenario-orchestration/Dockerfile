FROM golang:1.23-alpine AS builder

WORKDIR /app
ENV GOPROXY=https://goproxy.cn,direct

# 复制依赖文件
COPY go.mod ./

# 复制源代码
COPY . .

# 整理并下载依赖
RUN go mod tidy
RUN go mod download

# 编译
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/server

# 运行阶段
FROM alpine:latest

WORKDIR /root/

# 复制编译好的二进制文件
COPY --from=builder /app/main .

# 暴露端口
EXPOSE 8081

# 启动命令
CMD ["./main"]
