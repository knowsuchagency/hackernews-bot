import os

import aws_cdk as cdk
from aws_cdk import (
    aws_iam as iam,
)
from chalice.cdk import Chalice

RUNTIME_SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), os.pardir, "runtime"
)


class ChaliceApp(cdk.Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        table = topic = "hackernews_python_stories"

        self.chalice = Chalice(
            self,
            "ChaliceApp",
            source_dir=RUNTIME_SOURCE_DIR,
            stage_config={"environment_variables": {"TOPIC": topic}},
        )

        self.role = self.chalice.get_role("DefaultRole")

        self.role.add_to_principal_policy(
            iam.PolicyStatement(
                sid="grantTableAccess",
                actions=[
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    "dynamodb:Get*",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWrite*",
                    "dynamodb:CreateTable",
                    "dynamodb:Delete*",
                    "dynamodb:Update*",
                    "dynamodb:PutItem",
                ],
                resources=[f"arn:aws:dynamodb:*:*:table/{table}"],
            )
        )
