FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src
EXPOSE 8000 8501
CMD ["uvicorn", "fundlens.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
