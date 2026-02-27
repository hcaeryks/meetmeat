FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM alpine:3

RUN apk add --no-cache libstdc++ libgcc

COPY --from=oven/bun:alpine /usr/local/bin/bun /usr/local/bin/bun

WORKDIR /app

COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./

ENV PORT=3000
EXPOSE 3000

CMD ["bun", "build/index.js"]
