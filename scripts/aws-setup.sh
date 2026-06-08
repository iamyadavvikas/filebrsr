#!/usr/bin/env bash
# One-time AWS setup for FileBRSR ECR-based deploy.
# Creates: 2 ECR repos, 1 IAM user for GitHub Actions, attaches ECR pull policy to EC2.
#
# Run locally with AWS CLI configured (admin creds).
# Idempotent — safe to re-run.

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Account: $ACCOUNT_ID   Region: $AWS_REGION"
echo "ECR registry: $ECR_REGISTRY"
echo

# --- 1. Create ECR repos (with image scanning + lifecycle) ---
for REPO in filebrsr-frontend filebrsr-backend; do
  echo "→ ECR repo: $REPO"
  aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" \
    >/dev/null 2>&1 || \
    aws ecr create-repository \
      --repository-name "$REPO" \
      --region "$AWS_REGION" \
      --image-scanning-configuration scanOnPush=true \
      --image-tag-mutability MUTABLE \
      >/dev/null

  # Lifecycle: keep last 20 tagged + expire untagged after 7 days
  aws ecr put-lifecycle-policy \
    --repository-name "$REPO" \
    --region "$AWS_REGION" \
    --lifecycle-policy-text '{
      "rules": [
        {"rulePriority":1,"description":"Expire untagged >7d","selection":{"tagStatus":"untagged","countType":"sinceImagePushed","countUnit":"days","countNumber":7},"action":{"type":"expire"}},
        {"rulePriority":2,"description":"Keep last 20 tagged","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":20},"action":{"type":"expire"}}
      ]
    }' >/dev/null
done

# --- 2. Create IAM user for GitHub Actions (ECR push only) ---
GHA_USER="filebrsr-gha-ecr"
echo "→ IAM user: $GHA_USER"
aws iam get-user --user-name "$GHA_USER" >/dev/null 2>&1 || \
  aws iam create-user --user-name "$GHA_USER" >/dev/null

# Inline policy: push to our two repos only
aws iam put-user-policy \
  --user-name "$GHA_USER" \
  --policy-name ecr-push \
  --policy-document "{
    \"Version\":\"2012-10-17\",
    \"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":\"ecr:GetAuthorizationToken\",\"Resource\":\"*\"},
      {\"Effect\":\"Allow\",
       \"Action\":[
         \"ecr:BatchCheckLayerAvailability\",\"ecr:CompleteLayerUpload\",
         \"ecr:InitiateLayerUpload\",\"ecr:PutImage\",\"ecr:UploadLayerPart\",
         \"ecr:BatchGetImage\",\"ecr:GetDownloadUrlForLayer\"
       ],
       \"Resource\":[
         \"arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/filebrsr-frontend\",
         \"arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/filebrsr-backend\"
       ]
      }
    ]
  }"

echo
echo "→ Creating access key for $GHA_USER (PRINT ONCE — save immediately)"
KEY_JSON="$(aws iam create-access-key --user-name "$GHA_USER")"
ACCESS_KEY="$(echo "$KEY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["AccessKey"]["AccessKeyId"])')"
SECRET_KEY="$(echo "$KEY_JSON" | python3 -c 'import json,sys;print(json.load(sys.stdin)["AccessKey"]["SecretAccessKey"])')"

echo
echo "============================================================"
echo "SAVE THESE — they are shown ONCE."
echo "------------------------------------------------------------"
echo "AWS_ACCESS_KEY_ID     = $ACCESS_KEY"
echo "AWS_SECRET_ACCESS_KEY = $SECRET_KEY"
echo "ECR_REGISTRY          = $ECR_REGISTRY"
echo "============================================================"
echo
echo "Add as GitHub repo secrets:"
echo "  gh secret set AWS_ACCESS_KEY_ID     --repo ydvikasiitkgp-arch/filebrsr --body '$ACCESS_KEY'"
echo "  gh secret set AWS_SECRET_ACCESS_KEY --repo ydvikasiitkgp-arch/filebrsr --body '$SECRET_KEY'"
echo "  gh secret set ECR_REGISTRY          --repo ydvikasiitkgp-arch/filebrsr --body '$ECR_REGISTRY'"
echo
echo "Also add (you already have NEXT_PUBLIC_* in .env.local — copy them):"
echo "  gh secret set NEXT_PUBLIC_SUPABASE_URL      --repo ydvikasiitkgp-arch/filebrsr --body '...'"
echo "  gh secret set NEXT_PUBLIC_SUPABASE_ANON_KEY --repo ydvikasiitkgp-arch/filebrsr --body '...'"
echo "  gh secret set NEXT_PUBLIC_POSTHOG_KEY       --repo ydvikasiitkgp-arch/filebrsr --body '...'"
echo
echo "--- EC2 INSTANCE ROLE ---"
echo "Attach managed policy 'AmazonEC2ContainerRegistryReadOnly' to the IAM role"
echo "currently attached to the EC2 instance (or create one and attach it)."
echo "Console: EC2 → Instances → select → Actions → Security → Modify IAM role"
echo
echo "If the box has NO instance role yet, run:"
cat <<'EOR'
  ROLE=filebrsr-ec2-role
  aws iam create-role --role-name $ROLE --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'
  aws iam attach-role-policy --role-name $ROLE \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
  aws iam create-instance-profile --instance-profile-name $ROLE
  aws iam add-role-to-instance-profile --instance-profile-name $ROLE --role-name $ROLE
  # then in console: attach $ROLE instance profile to the EC2
EOR
