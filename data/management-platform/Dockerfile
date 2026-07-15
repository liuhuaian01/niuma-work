FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /niuma-mgmt .

FROM alpine:3.19
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /niuma-mgmt /usr/local/bin/niuma-mgmt
COPY schema.sql /etc/niuma/schema.sql
EXPOSE 8080
CMD ["niuma-mgmt"]
