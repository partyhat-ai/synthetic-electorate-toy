alert_email = "cam@partyhat.ai"

# The deploy role's trusted sub: this repo's immutable subject prefix, as
# GitHub reports it (GET repos/partyhat-ai/synthetic-voters-toy/actions/oidc/customization/sub),
# plus main. Only a workflow running on main can assume the role; a branch,
# tag, pull request or environment gets a different sub.
github_oidc_sub = "repo:partyhat-ai@44511702/synthetic-voters-toy@1400481223:ref:refs/heads/main"
