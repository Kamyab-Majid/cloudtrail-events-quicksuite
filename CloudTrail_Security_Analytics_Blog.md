 # Building enterprise CloudTrail security analytics dashboards using Amazon Quicksuite 

by Vy Nguyen and Majid Kamyab on 2025-11-03 in Amazon QuickSuite, AWS CloudTrail, AWS Glue, AWS Step Functions, Security & Compliance, Management & Governance Permalink Share 

 

In today's complex cloud environments, monitoring and visualizing security events across your AWS infrastructure is crucial for maintaining compliance and detecting threats. Traditionally, creating comprehensive CloudTrail analytics dashboards in [Amazon QuickSight](https://aws.amazon.com/quickssight/) has been a manual, time-intensive process requiring multiple steps for data processing, transformation, and visualization. 

 

[Amazon QuickSuite](https://aws.amazon.com/quickssuite/) is a cloud-native business intelligence service that transforms this experience by enabling natural language interactions with your CloudTrail data. This blog explores how Amazon QuickSuite simplifies dashboard creation through AI-powered capabilities, allowing you to reduce complex multi-step processes into intuitive prompts. Learn how you can quickly generate insightful security analytics and compliance visualizations from your CloudTrail logs. Discover how automated data processing pipelines help you create dynamic dashboards, saving valuable time while maintaining accuracy, and providing real-time insights into your organization's security posture. Whether you're a security analyst, compliance officer, or cloud architect, this guide demonstrates how modern analytics revolutionizes the way you monitor and report on AWS security events. 

 

Furthermore, this solution provides comprehensive visibility into your cloud security through custom analytical views. Create visualizations to monitor user activities, track resource changes, identify security anomalies, and maintain compliance across your AWS environment to better understand your security landscape. 

 

## Solution Overview 

 

**Figure 1 – Architecture diagram** 

 

The solution leverages several AWS services to automate CloudTrail log processing and utilize Amazon QuickSuite to visualize security data. AWS CloudTrail continuously logs API calls and writes encrypted logs to Amazon S3. An automated processing pipeline using AWS Step Functions orchestrates AWS Glue jobs that transform raw CloudTrail logs into optimized Apache Iceberg format. Amazon Athena provides analytical views over the processed data, which Amazon QuickSuite connects to for creating interactive security dashboards. 

 

The solution is deployed using AWS Cloud Development Kit (AWS CDK) to create the resources, including Amazon S3 bucket for log storage, AWS KMS key for encryption, AWS Glue database and jobs for data processing, AWS Step Functions for orchestration, Amazon EventBridge for scheduling, and Amazon QuickSuite datasets and analysis dashboards. The solution operates on automated schedules: AWS Step Functions executes CloudTrail log processing every week, and AWS Glue crawler performs data synchronization with Amazon Athena database. Both scheduling intervals can be modified to align with specific organizational requirements. 

 

The CloudTrail processing pipeline collects comprehensive security metadata from all AWS API calls to provide the following security insights: 

 

- **User Activities** – Information on user types, principal IDs, and authentication methods 

- **API Operations** – Complete audit trail of all AWS service interactions 

- **Security Events** – Failed authentication attempts, access denied events, and policy changes 

- **Resource Changes** – Creation, modification, and deletion of AWS resources 

- **Compliance Data** – Administrative actions, cross-account access, and privileged operations 

 

Additionally, it utilizes AWS Step Functions and Lambda functions to intelligently process CloudTrail logs: 

 

- **Dynamic Scaling** – Automatically adjusts AWS Glue job capacity based on log volume 

- **Parallel Processing** – Processes multiple date partitions concurrently for efficiency 

- **Error Handling** – Implements retry logic and graceful failure handling 

- **Cost Optimization** – Right-sizes compute resources based on actual data volume 

 

This information is processed into Apache Iceberg format for optimal query performance. The analytical views in Amazon Athena provide pre-built abstractions for common security use cases, making it easy to create QuickSuite visualizations. 

 

## Prerequisites 

 

For this walkthrough, you must have the following: 

 

- AWS CLI configured with appropriate permissions 

- AWS Cloud Development Kit (AWS CDK) version 2.91.0 or later installed 

- Python 3.9 or later for CDK development 

- Node.js 18.x or later for CDK runtime 

- Amazon QuickSuite user account with Admin Pro or Author Pro permissions 

- IAM permissions for CloudTrail, Amazon S3, AWS Glue, Amazon Athena, and Amazon QuickSuite 

- An existing VPC (referenced in the CDK configuration) 

 

## Walkthrough 

 

We will deploy the solution using AWS CDK Stack to create the required resources. The CDK Stack can be deployed from any AWS account with appropriate permissions. The CloudTrail logs, processing pipeline, and QuickSuite dashboards will be created in the stack deployment account and region. 

 

After the deployment, I will walk through creating visuals using Amazon QuickSuite natural language capabilities. 

 

1. **Download the CDK code from the GitHub repository and deploy the Stack.** 

 

2. **In the CDK configuration, enter the following parameters:** 

   - Under the section: **Environment Configuration** 

     - **Account ID**: Your AWS account ID for resource deployment 

     - **Region**: AWS region for resource deployment (e.g., us-east-1) 

     - **Environment**: Environment name (e.g., sandbox, dev, prod) 

    

   - Under the section: **CloudTrail Configuration** 

     - **Log Expiration Days**: Number of days to retain CloudTrail logs (default: 14) 

     - **Multi-Region Trail**: Enable multi-region CloudTrail logging 

     - **Include Global Services**: Include AWS global service events 

    

   - Under the section: **Processing Configuration** 

     - **Glue Worker Count**: Number of Glue workers for processing (auto-scaled based on data volume) 

     - **Processing Schedule**: EventBridge schedule for automated processing (default: weekly) 

 

   ![CDK deployment parameters for CloudTrail analytics] 

    

   **Figure 2 – AWS CDK parameters – CloudTrail analytics deployment** 

 

3. **Navigate to the AWS CloudFormation console to view the resources created by the CDK Stack.** 

 

After the CDK deployment completes, wait for the CloudTrail to generate logs and the initial AWS Glue job execution to complete. By default, the EventBridge rule triggers processing weekly. For immediate processing, you can manually execute the Step Functions state machine. 

 

Follow these steps to run the initial processing: 

 

1. **Navigate to AWS Step Functions console** 

2. **Choose the state machine that starts with "CloudTrailLogsStepFunction-*"** 

3. **Choose Start execution to run the processing pipeline.** 

 

The Step Functions workflow will: 

- Check for CloudTrail log availability 

- Discover all daily log partitions using Lambda functions 

- Process logs in parallel using dynamically scaled Glue jobs 

- Update the Glue Data Catalog for Athena querying 

 

## Validate QuickSuite user and permissions 

 

**QuickSuite User Role:** 

 

1. Navigate to Amazon QuickSuite console and sign in 

2. Choose the user icon on top right and **Manage QuickSuite** 

3. Choose **Manage users** and choose the role **Admin Pro** for the QuickSuite user 

 

![Amazon QuickSuite permissions] 

 

**Figure 3 – Amazon QuickSuite user permissions** 

 

**QuickSuite permissions:** 

 

1. On the same page in the left menu, under **Permissions**, choose **AWS resources**. 

2. Choose **Amazon Athena** and **Amazon S3**. Under **Select S3 buckets**, select the S3 bucket created by the CDK template for CloudTrail logs. 

3. Choose **Save**. 

 

![Amazon QuickSuite access to S3 bucket and Athena] 

 

**Figure 4 – Amazon QuickSuite role permissions to S3 bucket** 

 

## Create analytical views in Athena 

 

Before creating QuickSuite visualizations, set up the analytical views in Amazon Athena: 

 

1. **Navigate to Amazon Athena console** 

2. **Select the `cloudtrail_logs` database** 

3. **Create the analytical views using the following SQL:** 

 

**Base Flattened View:** 

```sql 

CREATE OR REPLACE VIEW "cloudtrail_flattened" AS  

SELECT 

  eventversion, 

  eventtime, 

  event_time, 

  event_date, 

  region, 

  eventsource, 

  eventname, 

  sourceipaddress, 

  useridentity.type user_type, 

  useridentity.principalid user_principal_id, 

  useridentity.arn user_arn, 

  useridentity.username user_name, 

  errorcode, 

  errormessage, 

  CASE WHEN errorcode IS NOT NULL THEN 1 ELSE 0 END is_failed, 

  CASE WHEN useridentity.type = 'Root' THEN 1 ELSE 0 END is_root_user, 

  CASE  

    WHEN eventname LIKE '%Create%' THEN 'Create' 

    WHEN eventname LIKE '%Delete%' THEN 'Delete' 

    WHEN eventname LIKE '%Update%' OR eventname LIKE '%Modify%' THEN 'Update' 

    WHEN eventname LIKE '%Get%' OR eventname LIKE '%Describe%' THEN 'Read' 

    ELSE 'Other' 

  END operation_type 

FROM cloudtrail_events 

WHERE event_date >= current_date - INTERVAL '90' DAY; 

``` 

 

## Create Visuals using Amazon QuickSuite 

 

1. On the QuickSuite home page, choose **Analysis** and create a new analysis. 

2. Choose **Athena** as the data source and select the `cloudtrail_logs` database. 

3. Under **Visuals**, choose the **Build** icon. This opens a side panel to enter natural language queries. 

4. Following are example prompts to generate security visualizations. You can customize the prompts and visuals as required. 

 

### Security Events by Type 

 

This visual displays the distribution of different security event types, providing insights into the most common security activities in your environment. 

 

- Enter the prompt as **"Create a pie chart for count of events by alert_type from cloudtrail_security_events"** and choose **BUILD**. 

- Alternatively, you can enter the prompt as **"Create a visual for security events by type"** to let Amazon Q decide on the visual type. 

- Amazon QuickSuite will generate the visual. Choose **Add to Analysis** and resize the visual as required. 

- Double-click on the heading to edit and update to **"Security Events by Type"** 

 

![Create visuals using Amazon QuickSuite] 

 

**Figure 5 – Build visual using Amazon QuickSuite** 

 

### Failed API Calls by Service 

 

- Enter the prompt as **"Create a bar chart for count of failed events by eventsource from cloudtrail_flattened where is_failed equals 1"** and choose **BUILD**. 

- Choose **Add to Analysis** and resize the visual as required. Update the visual heading. 

- Follow the same steps for other visuals as described below with different prompts. 

 

![Failed API calls by AWS service] 

 

**Figure 6 – Failed API calls by service** 

 

### Root User Activity Timeline 

 

Prompt: **"Create a line chart for count of events by event_date from cloudtrail_flattened where is_root_user equals 1"** 

 

![Root user activity over time] 

 

**Figure 7 – Root user activity timeline** 

 

### User Activity Summary 

 

Prompt: **"Create a table showing user_principal_id, total_api_calls, active_days, services_used from cloudtrail_user_summary"** 

 

### API Operations by Type 

 

Prompt: **"Create a donut chart for count of events by operation_type from cloudtrail_flattened"** 

 

![CloudTrail security operations dashboard] 

 

**Figure 8 – Security Operations Dashboard** 

 

## AWS Security-Specific Visuals 

 

The following visuals showcase detailed security information derived from CloudTrail events, providing valuable insights into AWS security posture and compliance requirements. 

 

Following are the prompts to create security-focused visuals: 

 

### Policy Changes Over Time 

 

- Prompt: **"Create a line chart for count of events by event_date from cloudtrail_security_events where alert_type equals 'Policy Change'"** 

- Choose null or empty data from the visual and choose **Exclude null**. Choose **Add to Analysis** to add the visual. 

- To add a text heading in the dashboard, choose **Add Text** icon from the top and edit to **"Security Dashboard"**. 

 

### Access Denied Events by IP 

 

Prompt: **"Create a bar chart for count of events by sourceipaddress from cloudtrail_security_events where alert_type equals 'Access Denied'"** 

 

### Resource Changes by Region 

 

Prompt: **"Create a map visualization for count of events by region from cloudtrail_resource_changes"** 

 

### High-Risk Activities 

 

Prompt: **"Create a pivot table with event_date, user_type, eventname, sourceipaddress from cloudtrail_security_events where severity equals 'High'"** 

 

### Administrative Actions 

 

Prompt: **"Create a timeline showing eventname, user_principal_id, event_time from cloudtrail_flattened where eventname contains 'Create' or eventname contains 'Delete'"** 

 

![Amazon QuickSuite AWS security dashboard] 

 

**Figure 9 – AWS Security Analytics Dashboard** 

 

## Compliance Monitoring 

 

The compliance sheet is utilized to create compliance-specific visualizations, particularly focusing on regulatory requirements and security best practices. Generate visuals that highlight compliance violations and provide comprehensive audit trails. 

 

1. From the top of the sheet, choose **Compliance** sheet 

2. Following are prompt examples for compliance-specific visuals: 

 

### Resource Creation Compliance 

 

Prompt: **"Create a pie chart for count of events by operation_type from cloudtrail_resource_changes where managementevent equals true"** 

 

### Cross-Account Access Monitoring 

 

Prompt: **"Create a table showing user_account_id, recipientaccountid, eventname, event_time from cloudtrail_flattened where user_account_id != recipientaccountid"** 

 

### Privileged Operations Audit 

 

Prompt: **"Create a bar chart for count of events by eventname from cloudtrail_flattened where user_type equals 'Root' or eventname contains 'Policy'"** 

 

### Failed Authentication Attempts 

 

Prompt: **"Create a line chart for count of events by event_date from cloudtrail_security_events where alert_type equals 'Failed Login'"** 

 

### Security Configuration Changes 

 

Prompt: **"Create a pivot table with event_date, region, eventname, user_principal_id, sourceipaddress from cloudtrail_security_events where eventname contains 'Security' or eventname contains 'Policy'"** 

 

![CloudTrail compliance monitoring dashboard] 

 

**Figure 10 – Compliance Dashboard** 

 

Once the visuals are created, choose **Publish** to publish the dashboard. Additionally, you can leverage Amazon QuickSuite to get detailed information or interact with the dashboard to answer security questions. For example, to get the list of failed login attempts, the prompt **"Show me all failed authentication events in the last 7 days"** can provide immediate answers. 

 

## Performance Optimization 

 

### Query Performance 

 

The Apache Iceberg format provides several performance benefits for CloudTrail analytics: 

- **Partition Pruning**: Queries automatically filter by date partitions 

- **Column Pruning**: Only required columns are read from storage 

- **Predicate Pushdown**: Filters are applied at the storage level 

- **Schema Evolution**: Tables can evolve without breaking existing queries 

 

### Cost Optimization 

 

Implement these strategies to manage costs: 

- **Lifecycle Policies**: Automatically delete old logs after retention period 

- **Dynamic Scaling**: Glue jobs scale based on actual data volume 

- **Partitioning**: Date-based partitioning reduces scan costs 

- **Query Limits**: Set appropriate limits in QuickSuite dashboards 

 

### Monitoring Recommendations 

 

Monitor the following metrics: 

- Step Functions execution success rate and duration 

- Glue job execution time and DPU utilization 

- Athena query performance and data scanned 

- S3 storage usage and access patterns 

- QuickSuite dashboard usage and refresh frequency 

 

## Cleanup 

 

To delete the resources: 

 

1. **Navigate to the AWS CloudFormation console** 

2. **Choose Stacks and choose stack named CloudTrailWithKmsStack** 

3. **Choose Delete and Delete stack** 

4. **Navigate to Amazon QuickSuite console** 

5. **Delete the Dashboard, Analyses and the Dataset** 

6. **Remove Athena views:** 

```sql 

DROP VIEW cloudtrail_user_summary; 

DROP VIEW cloudtrail_security_events; 

DROP VIEW cloudtrail_daily_metrics; 

DROP VIEW cloudtrail_resource_changes; 

DROP VIEW cloudtrail_flattened; 

``` 

 

## Conclusion 

 

In this blog post, we demonstrated how Amazon QuickSuite simplifies the creation of CloudTrail security analytics dashboards. By leveraging natural language interactions and automated data processing pipelines, what was once a complex, multi-step process has been transformed into simple, intuitive prompts that generate comprehensive security visualizations. This solution saves valuable time and provides real-time insights into security events, compliance status, and threat detection across your AWS environment. 

 

Furthermore, Amazon QuickSuite enables interactive querying of your CloudTrail data through natural language prompts, allowing you to quickly investigate security incidents and compliance questions. The combination of AWS services, including CloudTrail, Step Functions, Glue, Athena, and QuickSuite, enables organizations to maintain better security visibility while simplifying the monitoring and reporting process. Whether you're managing security compliance, investigating incidents, or monitoring AWS resource changes, this solution offers a streamlined approach to security analytics and threat detection. Transform your security monitoring today by implementing AI-powered CloudTrail analytics and gain unprecedented visibility into your AWS environment. 

 

To learn more about AWS CloudTrail security best practices, visit our [AWS CloudTrail User Guide](https://docs.aws.amazon.com/cloudtrail/). 

 

## About the Authors 

 

**[Author Name]** 

 

[Author bio and headshot - Brief description of expertise in AWS security, CloudTrail, and analytics solutions] 

 

**[Author Name]** 

 

[Author bio and headshot - Brief description of expertise in AWS data analytics, QuickSuite, and visualization] 

 

**[Author Name]** 

 

[Author bio and headshot - Brief description of expertise in AWS infrastructure, CDK, and automation] 

 

--- 

 

**GitHub Repository**: The complete code for this solution is available in the [GitHub repo](https://github.com/your-org/infra-sandbox).  

uicksuite/ 

Title: Usually starts with a verb in the imperative or a noun phrase and mentions relevant AWS services. For example, “Add calculations in Amazon QuickSight” or “New period functions available in Amazon QuickSight”. For good display, titles should be under 75 characters (including spaces). 

Intro: No header. For good SEO, the intro should mention the purpose of the post, using keywords from the title and mentioning relevant AWS services, within the first paragraph. 

Solution overview: More details about the architecture or services used, an architecture diagram if needed, and a numbered list of any procedures if needed. 

Prerequisites: Include any resources needed to build the solution that aren’t included in the instructions. Such as IAM roles, access to services, and other resources. In addition clearly state the version of the tool/software used. For example, "For this post we are using MYSQL 8.0.29". 

Procedure: Break up into sections as needed. Sections should mirror the steps outlined in the solution. 

    Download the CloudFormation template from the GitHub respository and deploy the Stack. 

    S3 bucket 

    Cloudtrail events 

    Stepfunction state machine 

    Takes care of the ingestion to glue catalog to be queryable in athena 

    In the parameters area, enter the following parameters: 

MAJID !!!!!!!!! 

Under the section: SSM Resource Data Sync and Custom inventory configuration 

Amazon S3 bucket: Name of the Amazon S3 bucket used for AWS Systems Manager resource data sync 

Target type: Target type for custom inventory association. Specify ALL for all instances, TAG for tag-based targets and enter the tag key and value in next parameter 

Tag key for targeting instances 

Tag value for targeting instances 

Under the section: AWS Accounts Options: 

AWS Organization ID: AWS Organization root ID (r-xxx) or Organization Unit ID (ou-xxx). 

AWS Account IDs: List of AWS Accounts IDs to be deployed in the Organization or OU. (Accounts must be member of the specified Org/OU). Leave empty to deploy to all accounts in the Organization or OU. 

AWS Account Regions: List of AWS Regions 

CloudFormation template parameters for Organization deployment 

 

Figure 2 – AWS CloudFormation parameters – Organization deployment 

 

To deploy to accounts without Organization setup: 

 

AWS Organization ID: Leave the field empty 

AWS Account IDs: List of AWS Accounts IDs to be deployed (Accounts must not be part of any Organization) 

AWS Account Regions: List of AWS Regions 

CloudFormation parameters for accounts not part of Organization 

 

Figure 3 – AWS CloudFormation parameters for accounts not part of Organization 

 

Under the section: Amazon Athena 

Amazon Athena Database Name: Amazon Athena Database name for AWS Systems Manager resource data sync 

Under the section: Amazon Quick Suite 

Amazon Quick Suite user: Enter the Amazon Quick Suite username. 

 

    Navigate to Resources tab to view the resources created by the CloudFormation Stack. 

After the CloudFormation deployment completes, we can start executing the Step Function state machine to handle the ingestion of data from S3 bucket: 

 

Navigate to AWS Glue Crawlers console 

Choose the crawler which starts with “SSM-GlueCrawler-*” 

Choose Run to run the crawler. 

The Glue Crawler will crawl the Inventory data from central S3 bucket and updates on the Glue database ssm_datasync_resources. 

    Create Athena query 

    Create dashboard in quicksight 

Cleanup: Include steps to delete resources created during the procedure to avoid incurring charges for your readers. 

Conclusion: Summarize your post with a call to action. Additionally provide references/recommendations to other blog posts with related content. 

About the author(s): Includes list of authors with their brief bio and headshot. 

Intro paragraph 

 

Make sure your introductory paragraph clearly explains to the reader what this post will do for them or why they should read it. The value should be clearly stated in the first or second paragraph. Don’t walk your audience through multiple paragraphs of backgound before telling them what the value of the post is for them. 

Good examples: 

Big Data: 

Technical post 

Customer post 

Database: 

Technical post 

Customer post 

Machine Learning: 

Technical post 

Customer post 

Service names 

 

Remember that your finished blog will be available online, so the more linking you can do to service info, the better. At least link the first mention of each service name. The service names include appropriate links for each service. Pay particular attention to the First use, Subsequent use, Do not use, and Notes columns. 

Note: When you link to a first use name that includes parenthesis, include the parenthesis in the link. For example: AWS Cloud Development Kit (AWS CDK). 

Hyperlinks 

 

For a customer post, link the first mention of the customer to their official website. 

Use wording like the following examples. 

For more information about [a topic], refer to [link, using title of page or post for hyperlinked text]. 

For more details on [a topic], refer to [link, using title of page or post for hyperlinked text]. 

For instructions on [doing a procedure], refer to [link, using title of page or post for hyperlinked text]. 

The full code is available on the GitHub repo. (use “GitHub repo” as hyperlinked text) 

You can also use “the [service] Developer Guide” or “the [service] User Guide” if linking to that main page. 

Images and diagrams 

 

Refer to this resource for creating architecture diagrams. 

Make sure each image is introduced or described in the narrative of the post. 

Avoid using too many images - instead try to combine them into a gif. 

Each image must have a numbered and descriptive caption so that references to images and diagrams are clear, even if the blog is translated or read through a screen reader. 

For accessibility, images must be thoroughly described immediately before or after they appear. 

Good examples: 

Big Data example 

Database example 

Machine Learning example 

Make sure all service names used in images comply with the service names. For brevity and to conserve space, you can use the “subsequent mention” service names. For example, use “Amazon S3” instead of “Amazon Simple Storage (Amazon S3)”. 

Make sure any sensitive information such as account numbers, IDs, or ARNs is masked in screenshots. It’s recommended to use black or grey rectangles to mask the information. 

For more information about graphics, see the accessibility and graphics topics in the AWS Style Guide. 

Additional tip - To bring your screenshots to life try adding text bubbles like in this blog post. 

POV 

 

Use second person (“you”) throughout the blog post, instead of third person (“the customer… they should”) or first person (“I created this solution”). 

Keep the focus on the experience of the reader, and use “I” or “we” sparingly. 

It’s okay to use first person (“I” or “we”) in the intro, but you should move to second person (“you”) as soon as practical. 

Section headings 

 

Use section headings to clearly guide the reader through the post beginning with a Header 2. 

Amazon uses sentence case, not title case 

FUD and messaging guidelines 

 

Make sure you don’t use fear, uncertainty, doubt, or other scary language to explain issues and outline solutions. Don’t describe any AWS service as hard to use or confusing. 

Review the AWS Security Messaging Guidelines for details. <Internal - Kalyan will perform this action> 

For any service that’s a managed open source service, please acknowledge any open source contributions. This could be AWS-led or other contributions. 

Procedures 

 

Follow the AWS Style Guide procedure guidelines. 

All procedures need to have clear imperative headings, such as “Create IAM roles” or “Clean up resources”. 

The steps within procedures should be formatted as numbered lists of 5 to 7 steps, if possible. Longer procedures should be broken out into shorter procedures, where possible. 

Generally, a procedure should look like: 

Section heading: Do the thing (Feed a unicorn) 

Intro: Description of what will be done, or what will be accomplished by doing the thing. (All unicorns need feeding. To guarantee the best rainbows, you’ll want to source and provide the highest quality, organic, rainbow ingredients). 

Sub-heading: To do the thing (To feed a unicorn) 

Steps: Steps to do the thing. If there’s more than one step, number them. Each step should cover one action or one UI screen, and should end with a period. 

Procedures should avoid mouse or keyboard specific terms. Instead, use choose (for UI components), select (for selecting options such as checkboxes or resources), and enter (for text or commands). Avoid click or type. 

Any items that the user chooses should use bold formatting without quotes. 

Use the AWS Style procedure phrasing. 

“Choose” for UI elements and “select” for resources or options (do not use “click,” “hit,” or “strike). 

“Clear” to remove a previously selection option. 

“Press” for single key or key combination entries on a keyboard. For example: “Press Enter” or “Press Ctrl+Alt+Delete” 

Install/located in a folder, directory, path 

Install/located on a drive, instance 

Save/upload to a drive, Amazon S3 

On the console, dashboard, menu, page, tab, toolbar 

In the box, group, navigation pane, section, view 

This post has an example of procedures: Access Amazon S3 data managed by AWS Glue Data Catalog from Amazon SageMaker notebooks 

Fake names 

 

Please maintain your own security! Use approved fictitious names and make sure any and all identifying info is removed from screenshots. More safe names. 

Cleanup 

 

If your post includes a procedure that created any resources or accounts, include a cleanup section. 

The cleanup section should be between the procedure and conclusion. 

Include what resources to delete, a procedure to follow, or a link to instructions in the product documentation. 

Alternatively, tell the user what charges they might incur. 

Conclusion 

 

At the end of your post include a summary or conclusion section. At the end of this section add suggested next steps or a call to action - what would you like your readers to do after they have read your post? 

Good examples: 

Big Data Blog post 

Database Blog post 

Machine Learning Blog post 

It is also recommended to add references or recommendations to other blog posts with related content. 

Good examples: 

Big Data Blog post 

Database Blog post 

Machine Learning Blog post 

Language 

 

Don’t use words like simple and easy. It might come across as condescending or offensive. 

Spell out acronyms on first use and follow with the acronym in parenthesis. Once defined, use the acronym. For example, Machine learning (ML), Extract, transform, and load (ETL), Software as a service (SaaS). 

Something common like “database” doesn’t need the acronym explained in parentheses, it’s ok to say “database instance” the first time and then switch to “DB instance.” But don’t use “DB” on its own, use “database.” 

DO NOT use AZ for Availability Zone (except for Multi-AZ) 

Use simpler phrases 

Due to the fact that ->  because 

In order to ->  to 

All of the ->  all 

A large number of ->  many 

Take a look at ->  Review 

Carry out an evaluation ->  Evaluate 

Do a verification ->  Verify 

Make use of ->  Use 

You need to create ->  Create 

Additional ->  more 

Have an option to ->  can 

In the event that ->  if 

Leverage ->  use 

Both of ->  Both 

Blog / blog post ->  post (“blog” refers to the whole website, not an individual post) 

Currently ->  As of this writing 

Able to ->  can 

Each of ->  each 

Since ->  because (except when referring to time, like “Since its launch…”) 

As ->  because (when appropriate) 

For the purpose of ->  For 

etc. ->  and so on / and more (or just remove) 

Use words for better accessibility inclusion: 

Above ->  preceding 

Below ->  following 

See ->  observe (or rephrase entirely, for example, “In this graph, you can see an increase of 5 percent or The graph shows an increase of 5 percent”) 

Avoid the following words (see style guide for full list): 

Execute ->  run 

Abort or terminate ->  stop, cancel 

Master ->  primary, main leader 

Slave ->  replica, secondary, standby 

Hang ->  stop responding 

Avoid passive tense when possible, use active tense. 

Avoid future tense when possible, use present tense. 

Use contractions to sound more casual. 

Avoid starting sentences with “By” or with a verb ending with -ing. 

Examples of what not to do: 

By implementing this solution, you can achieve better cost optimization. 

Implementing this solution helps you achieve better cost optimization. 

Examples of better phrasing: 

You can improve cost optimization by implementing this solution. 

You can improve cost optimization with this solution. 

This solution can help you improve cost optimization. 

Punctuation 

 

Don’t use double spaces between sentences. 