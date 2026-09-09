FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt streamlit plotly pandas

COPY . .

# Expose Streamlit port
EXPOSE 8080

# Create an entrypoint script to run both FastAPI and Streamlit
RUN echo '#!/bin/bash\n\
uvicorn main:app --host 0.0.0.0 --port 8000 &\n\
streamlit run dashboard.py --server.port ${PORT:-8080} --server.address 0.0.0.0\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
