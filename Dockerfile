FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn
CMD ["python", "main.py"]

