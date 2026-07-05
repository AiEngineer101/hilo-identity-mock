FROM python:3.11-alpine
WORKDIR /app
COPY server.py .
ENV PORT=10000
EXPOSE 10000
CMD ["python3", "server.py"]
