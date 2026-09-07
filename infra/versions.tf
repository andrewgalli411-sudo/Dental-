terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state. Create this bucket + DynamoDB lock table once, by hand, before
  # `terraform init` (chicken-and-egg — state can't store its own backend).
  backend "s3" {
    # bucket         = "verifi-tfstate-<your-account-id>"
    # key            = "verifi-dental/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "verifi-tf-locks"
    # encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = "verifi-dental"
      ManagedBy = "terraform"
      # PHI system — helps scope access reviews and cost.
      DataClass = "phi"
    }
  }
}
