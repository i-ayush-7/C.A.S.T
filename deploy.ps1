$envVars = ((Get-Content .env) | Where-Object { $_ -match '=' -and $_ -notmatch '^#' } | ForEach-Object {
    $parts = $_ -split '=', 2
    $key = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    "$key=$value"
}) -join ','

Write-Host "Deploying Agentic Cinema to Google Cloud Run..."
gcloud run deploy agentic-cinema --source . --region us-central1 --allow-unauthenticated --port 8080 --set-env-vars="$envVars"
Write-Host "Deployment complete!"
