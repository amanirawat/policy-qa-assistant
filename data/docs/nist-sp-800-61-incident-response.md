---
title: NIST SP 800-61 Rev. 3 - Incident Response Recommendations
publisher: NIST
url: https://csrc.nist.gov/pubs/sp/800/61/r3/final
note: Starter summary written for this project in plain language. Verify against the official publication before relying on it.
---

# Incident Response (NIST SP 800-61)

## What counts as a security incident
A cybersecurity incident is an occurrence that actually or imminently jeopardizes the confidentiality, integrity, or availability of information or systems, or that violates security policies. Examples include malware infections, unauthorized access to accounts, lost or stolen devices holding sensitive data, and successful phishing attacks.

## Incident response and the Cybersecurity Framework 2.0
Revision 3 of SP 800-61 organizes incident response around the six functions of the NIST Cybersecurity Framework 2.0. Govern, Identify, and Protect cover preparation work done before an incident. Detect, Respond, and Recover cover the activities that happen when an incident occurs. Lessons learned from each incident should feed back into improving all six functions.

## Incident response lifecycle
The incident handling lifecycle has four broad phases: preparation; detection and analysis; containment, eradication, and recovery; and post-incident activity. Preparation includes building an incident response plan, defining roles, and setting up communication channels before anything goes wrong.

## Detection and analysis
Incidents are detected through precursors, which are signs an incident may occur in the future, and indicators, which are signs an incident may have occurred or is happening now. Alerts from security tools, unusual log activity, and reports from employees are common indicators. Analysts should triage and prioritize incidents based on functional impact, information impact, and how recoverable the affected systems are.

## Containment, eradication, and recovery
Containment limits the damage of an incident, for example by isolating an infected device from the network or disabling a compromised account. Eradication removes the cause, such as deleting malware and closing exploited vulnerabilities. Recovery restores systems to normal operation and confirms they are functioning securely.

## Preserving evidence
Evidence related to an incident should be preserved and documented. Logs, affected systems, and relevant files should not be deleted or wiped before they are collected. A chain of custody should be maintained for any evidence that may be needed for legal action.

## Employee reporting of suspected incidents
Employees who notice suspicious activity, such as a strange pop-up, an unexpected password reset, a lost laptop, or an email they clicked by mistake, should report it immediately through the organization's designated reporting channel. Fast reporting shortens the time attackers have to cause damage. Employees should not try to investigate or fix the problem on their own.

## Roles and communication
Effective incident response involves more than the security team. Leadership, legal counsel, public affairs, human resources, and IT operations may all have roles. Organizations should define in advance who is notified, who makes decisions, and how information is shared internally and externally.

## Post-incident activity and lessons learned
After a significant incident, the organization should hold a lessons-learned review to document what happened, what worked, what did not, and what should change. These findings should be used to update policies, controls, and the incident response plan.
