FROM node:22-alpine

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

WORKDIR /workspace/apps/web

COPY apps/web/package*.json ./
RUN npm ci

COPY apps/web ./

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
