param(
  [Parameter(Mandatory = $true)][string]$Bucket,
  [string]$StackName = "CodeBuddyStack",
  [string]$Region = "ap-northeast-2",
  [Parameter(Mandatory = $true)][string]$AgentId,
  [Parameter(Mandatory = $true)][string]$AgentAliasId,
  [Parameter(Mandatory = $true)][string]$GitHubToken,
  [Parameter(Mandatory = $true)][string]$GitHubWebhookSecret,
  [Parameter(Mandatory = $true)][string]$DiscordWebhookUrl,
  [string]$EnableBedrock = "true",
  [string]$Profile = "codebuddy"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Artifacts = Join-Path $Root "artifacts"
$ZipPath = Join-Path $Artifacts "codebuddy-lambda.zip"
$Key = "codebuddy/codebuddy-lambda.zip"

New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null
if (Test-Path $ZipPath) {
  Remove-Item -LiteralPath $ZipPath
}

Compress-Archive -Path (Join-Path $Root "lambda\*") -DestinationPath $ZipPath
aws s3 cp $ZipPath "s3://$Bucket/$Key" --region $Region --profile $Profile

aws cloudformation deploy `
  --region $Region `
  --profile $Profile `
  --template-file (Join-Path $Root "cloudformation\template.yaml") `
  --stack-name $StackName `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides `
    LambdaS3Bucket=$Bucket `
    LambdaS3Key=$Key `
    AgentId=$AgentId `
    AgentAliasId=$AgentAliasId `
    EnableBedrock=$EnableBedrock `
    GitHubToken=$GitHubToken `
    GitHubWebhookSecret=$GitHubWebhookSecret `
    DiscordWebhookUrl=$DiscordWebhookUrl

aws cloudformation describe-stacks `
  --region $Region `
  --profile $Profile `
  --stack-name $StackName `
  --query "Stacks[0].Outputs"
