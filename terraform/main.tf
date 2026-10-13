terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

resource "aws_s3_bucket" "securevault" {
  bucket = "securevault-demo-2026-xyz"
}

resource "aws_s3_bucket_public_access_block" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "securevault" {
  bucket = aws_s3_bucket.securevault.id

  versioning_configuration {
    status = "Enabled"
  }
}
