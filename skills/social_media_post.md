# Skill: Social Media Post

## Description
Create and publish posts across LinkedIn, Facebook, Instagram, and Twitter/X.

## Trigger
User requests a social media post, or daily summary generates one.

## Steps
1. Generate post content (or use provided content)
2. Create post file in /Pending_Approval with platform tags
3. Wait for human approval (file moved to /Approved)
4. Approval watcher triggers execution
5. Dispatch to target platforms via post_everywhere.py
6. Log results and move to /Done

## Platforms
- LinkedIn: linkedin_playwright.py (text posts)
- Facebook: facebook_playwright.py (text posts)
- Instagram: instagram_playwright.py (image + caption)
- Twitter/X: twitter_playwright.py (280 char tweets)

## Safety
All posts require human approval before publishing.
