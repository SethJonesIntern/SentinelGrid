# Updates the App Runner backend image: re-auth -> build -> tag -> push -> deploy.
# Usage: ./update.ps1   (run from the HoneyNet-Backend folder)
#
# NOTE: the image now bundles the ML pipeline (machine-learning/), so it MUST be
# built from the REPO ROOT with -f HoneyNet-Backend/Dockerfile. This script does
# that automatically via $PSScriptRoot regardless of where you launch it.

$ErrorActionPreference = "Stop"

# --- Config: edit these if your setup differs -------------------------------
$AccountId   = "310454703339"
$Region      = "us-east-1"
$RepoName    = "honeynet-backend"
# Optional: set your App Runner service ARN to auto-trigger a deploy after push.
# Leave blank if automatic deployments are enabled on the service.
$ServiceArn  = ""
# ---------------------------------------------------------------------------

$Registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$Image    = "$Registry/$RepoName`:latest"

# Build context is the repo root (parent of this script's HoneyNet-Backend dir),
# so the sibling machine-learning/ pipeline is included in the image.
$Dockerfile = Join-Path $PSScriptRoot "Dockerfile"
$RepoRoot   = Split-Path $PSScriptRoot -Parent

Write-Host "1/4 Logging Docker in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $Registry

Write-Host "2/4 Building image (context: $RepoRoot)..." -ForegroundColor Cyan
docker build --platform linux/amd64 -f $Dockerfile -t $RepoName $RepoRoot

Write-Host "3/4 Tagging and pushing..." -ForegroundColor Cyan
docker tag "$RepoName`:latest" $Image
docker push $Image

if ($ServiceArn) {
    Write-Host "4/4 Triggering App Runner deployment..." -ForegroundColor Cyan
    aws apprunner start-deployment --service-arn $ServiceArn --region $Region
} else {
    Write-Host "4/4 Push complete. If auto-deploy is OFF, hit 'Deploy' in the App Runner console." -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Green
