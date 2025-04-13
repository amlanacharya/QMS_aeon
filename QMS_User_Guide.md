# QMS (Queue Management System) User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Customer Guide](#customer-guide)
3. [Employee Guide](#employee-guide)
4. [Administrator Guide](#administrator-guide)
5. [Troubleshooting and FAQs](#troubleshooting-and-faqs)

## Introduction

The Queue Management System (QMS) is designed to streamline customer service by efficiently managing customer queues. This guide will help you understand how to use the system based on your role.

### Key Features

- **Token Generation**: Customers can generate tokens with specific visit reasons
- **Real-time Queue Updates**: Live display of current and next tokens
- **Employee Dashboard**: Manage tokens and serve customers efficiently
- **Admin Controls**: Complete system management and analytics
- **Analytics**: Track service times, token statistics, and employee performance

## Customer Guide

### Generating a Token

1. Visit the main page of the QMS system
2. Under "Get Your Token", select your visit reason from the dropdown menu
   - If your reason isn't listed, select "Other" and specify your reason
3. Enter your phone number
4. Enter your name
5. Click "Generate Token"
6. You'll receive a token number - you can print this for reference

### Tracking Your Token

1. The main screen displays:
   - **NOW SERVING**: The token currently being served (with a green "LIVE" indicator)
   - **NEXT**: The next token in the queue
2. Wait for your token number to be called
3. When your token appears under "NOW SERVING", proceed to the service desk

## Employee Guide

### Logging In

1. From the main page, click "Employee Login"
2. Enter your employee ID and password
3. Click "Login"

### Dashboard Overview

The Employee Dashboard is divided into several sections:

#### Employee Information
- Shows your name, role, and duty status
- Displays statistics about tokens you've served
- Shows your current status (On Duty/Off Duty)

#### Current Token Status
- **Now Serving**: Displays the current token being served
- **Next Token**: Shows the next token in the queue with a "Serve Next" button
- **Recall** button: Use to recall the current token if the customer doesn't respond
- **Skip** button: Use to skip the current token and move to the next one

#### Queue Management
- **Stop Queue/Start Queue**: Toggle to pause or resume token generation
- **Reset Token Counter**: Reset the token numbering to 0
- **View Analytics**: Access service statistics and performance metrics

#### Generate New Token
- Create tokens for walk-in customers
- Select visit reason, enter phone number and customer name
- Click "Generate & Print Token"

#### Pending Tokens
- List of all pending tokens waiting to be served
- Actions for each token:
  - **Serve**: Serve this token immediately
  - **Print**: Print the token
  - **Edit**: Modify token details
  - **Delete**: Remove the token from the queue

#### Recently Served by You
- List of tokens you've recently served
- Actions for each token:
  - **Print**: Print the token
  - **Revert to Pending**: Undo a mistakenly served token

### Managing Tokens

#### Serving Tokens
1. Click "Serve Next" to serve the next token in queue, or
2. Find a specific token in the "Pending Tokens" list and click "Serve"
3. The token will move to "Now Serving" and the customer will be notified

#### Recalling a Token
If a customer doesn't respond when called:
1. Click the "Recall" button
2. The system will mark the token as recalled and notify the customer again

#### Skipping a Token
If you need to skip the current token:
1. Click the "Skip" button
2. Confirm the action
3. The token will be marked as skipped and the next token will be served

#### Reverting a Served Token
If you mistakenly mark a token as served:
1. Find the token in "Recently Served by You"
2. Click the "Revert to Pending" button (circular arrow icon)
3. The token will return to the pending queue

### Queue Control

#### Starting/Stopping the Queue
1. In the "Queue Management" section, click "Stop Queue" to temporarily prevent new token generation
2. Click "Start Queue" to resume token generation

#### Resetting the Token Counter
1. In the "Queue Management" section, click "Reset Token Counter"
2. Confirm the action
3. The next generated token will start from T001

### Starting and Ending Duty

1. Click "Start Duty" at the top of the dashboard to begin your shift
2. Click "End Duty" when your shift is complete

## Administrator Guide

Administrators have all the capabilities of employees plus additional system management features.

### Logging In

1. From the main page, click "Admin Login"
2. Enter the admin password
3. Click "Login"

### Dashboard Overview

The Admin Dashboard includes all employee features plus:

#### Queue Administration
- **System Management** section with additional controls:
  - **Analytics Dashboard**: Comprehensive system analytics
  - **Manage Employees**: Add, edit, or deactivate employee accounts
  - **Manage Visit Reasons**: Configure the reasons customers can select
  - **Export as CSV**: Export token data for external analysis
  - **Reset Database**: Clear all data (requires confirmation)

#### Token History
- Complete history of all tokens with detailed information
- Filter and search capabilities
- Actions for each token including reverting status

### Managing Employees

1. Click "Manage Employees" in the System Management section
2. Add new employees:
   - Enter employee ID, name, role, and password
   - Set active status
   - Click "Add Employee"
3. Edit existing employees:
   - Click the edit icon next to an employee
   - Update details and click "Update Employee"
4. Activate/Deactivate employees:
   - Click the toggle button next to an employee

### Managing Visit Reasons

1. Click "Manage Visit Reasons" in the System Management section
2. Add new reasons:
   - Enter reason code and description
   - Click "Add Reason"
3. Edit existing reasons:
   - Click the edit icon next to a reason
   - Update details and click "Update Reason"
4. Activate/Deactivate reasons:
   - Click the toggle button next to a reason

### Analytics

1. Click "Analytics Dashboard" to view system performance
2. View metrics including:
   - Average waiting time
   - Average service time
   - Tokens served per day/hour
   - Employee performance statistics
   - Visit reason distribution

### Data Management

#### Exporting Data
1. Click "Export as CSV" to download token data
2. Save the file to your computer for analysis

#### Resetting the Database
1. Click "Reset Database"
2. Enter the admin password to confirm
3. Choose whether to export data before deletion
4. Confirm the action

## Troubleshooting and FAQs

### Common Issues

#### Token Not Updating on Display
- Check if the queue is active (Admin or Employee can verify)
- Refresh the browser page
- Ensure the system is connected to the network

#### Employee Cannot Log In
- Verify the employee ID and password
- Check if the employee account is active
- Contact an administrator for assistance

#### Cannot Generate Tokens
- Check if the queue is active (may be paused)
- Ensure all required fields are filled out
- Try refreshing the page

### FAQs

**Q: How do I change my password?**  
A: Contact an administrator to reset your password.

**Q: What happens if I accidentally serve the wrong token?**  
A: Use the "Revert to Pending" option in the "Recently Served" section to return the token to the pending queue.

**Q: Can multiple employees be on duty at the same time?**  
A: Only one employee can be on duty at a time. When a new employee starts duty, the previous employee is automatically set to off duty.

**Q: How do I handle a customer with an urgent matter?**  
A: You can directly serve their token from the pending tokens list, bypassing the queue order.

**Q: What does the "Reset Token Counter" do?**  
A: It resets the token numbering sequence to start from T001 for the next token. This is typically done at the beginning of each day.

**Q: Can I customize the visit reasons?**  
A: Yes, administrators can add, edit, or deactivate visit reasons through the "Manage Visit Reasons" section.

---

For additional support, please contact your system administrator.
