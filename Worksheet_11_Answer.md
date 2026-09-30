# Work Plan — Jayraldine's Catering Reservation and Management System

---

## 1. The Estimates

We first timed our **planning phase** and then used the standard industry percentages for a typical business application to project the remaining phases. Our planning phase took **3 person-months** of actual effort. Since planning is expected to consume about 15% of the total effort, the whole project is estimated at **3 ÷ 0.15 = 20 person-months**. The same percentages were then applied to estimate each of the remaining phases.

| | Planning | Analysis | Design | Implementation |
| :--- | :---: | :---: | :---: | :---: |
| **Typical industry standards for business applications** | 15% | 20% | 35% | 30% |
| **Estimates based on actual figures for the first stage of the SDLC** | Actual: 3 person-months | Estimated: 4 person-months | Estimated: 7 person-months | Estimated: 6 person-months |

**Total estimated effort:** 3 + 4 + 7 + 6 = **20 person-months**

**Average staffing.** Dividing the total person-months of effort by the optimal schedule gives the average number of staff needed. For a **20 person-month** project targeted for completion in an optimal **5-month** schedule, the team should average **20 ÷ 5 = 4 full-time members** — which matches our four-member group. Because several modules can be built in parallel, the detailed schedule below compresses the calendar to roughly **4.5 months** (about 95 working days) of elapsed time.

---

## 2. Work Breakdown Structure (WBS)

The work plan is organized **by SDLC phase** — planning, analysis, design, and implementation. Each phase is a main task focused on its required deliverables, and within each task are the subtasks that detail the activities needed to complete it. The list is hierarchically numbered, forming the backbone of the project work plan.

| Task ID | Task Name | Duration (days) | Dependency | Status |
| :--- | :--- | :---: | :---: | :---: |
| **1** | **Planning Phase** | **15** | | Open |
| 1.1 | Project initiation and system request | 4 | | Open |
| 1.2 | Feasibility analysis (technical, economic, organizational) | 7 | 1.1 | Open |
| 1.3 | Develop project work plan and staffing plan | 4 | 1.2 | Open |
| **2** | **Analysis Phase** | **15** | 1 | Open |
| 2.1 | Requirements gathering and owner interviews | 6 | 1.3 | Open |
| 2.2 | Functional requirements and use case modeling | 5 | 2.1 | Open |
| 2.3 | Nonfunctional requirements definition | 3 | 2.1 | Open |
| 2.4 | Process modeling (Data Flow Diagrams) | 4 | 2.2 | Open |
| 2.5 | Data modeling (Entity Relationship Diagram) | 4 | 2.2 | Open |
| **3** | **Design Phase** | **16** | 2 | Open |
| 3.1 | Database design (PostgreSQL server + SQLite offline) | 8 | 2.5 | Open |
| 3.2 | System and network architecture design (client-server LAN) | 6 | 2.4 | Open |
| 3.3 | Desktop UI/UX design (PySide6 manager station) | 10 | 3.2 | Open |
| 3.4 | Tablet kiosk UI design (PWA / Android APK) | 8 | 3.2 | Open |
| 3.5 | Reports and document template design (PDF / Excel) | 5 | 3.1 | Open |
| **4** | **Implementation Phase** | **49** | 3 | Open |
| 4.1 | Database and backend core setup | 6 | 3.1 | Open |
| 4.2 | Booking and event calendar module | 10 | 4.1 | Open |
| 4.3 | Customer management module | 6 | 4.1 | Open |
| 4.4 | Menu package module | 8 | 4.1 | Open |
| 4.5 | Billing and payment module | 10 | 4.2, 4.4 | Open |
| 4.6 | Kitchen and inventory module | 8 | 4.4 | Open |
| 4.7 | Tablet kiosk and LAN sync engine | 12 | 4.2, 4.4 | Open |
| 4.8 | Reports and analytics dashboard | 8 | 4.5 | Open |
| 4.9 | Testing (unit, integration, UAT) | 10 | 4.7, 4.8 | Open |
| 4.10 | Deployment and installer packaging | 5 | 4.9 | Open |

*The duration shown for a phase (Task IDs 1–4) is the overall elapsed span of that phase, while its subtasks may run in parallel within the span.*

---

## 3. The Work Plan

The work plan lists each task with the team member assigned, the estimated start and finish dates, task dependencies, and status. The **Actual** columns are left blank at this stage; they will be filled in during execution so the team can track whether the project is ahead of or behind schedule and compute the duration variance. The project is scheduled from **Mon 7/7/25** to **Fri 11/14/25**.

| Task ID | Task Name | Assigned To | Est. Duration | Est. Start | Est. Finish | Actual Start | Actual Finish | Variance | Dependency | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | Planning Phase | Member 1 | 15 | Mon 7/7/25 | Fri 7/25/25 | | | | | Open |
| 1.1 | Project initiation and system request | Member 1 | 4 | Mon 7/7/25 | Thu 7/10/25 | | | | | Open |
| 1.2 | Feasibility analysis | Member 1 | 7 | Fri 7/11/25 | Mon 7/21/25 | | | | 1.1 | Open |
| 1.3 | Develop project work plan and staffing plan | Member 1 | 4 | Tue 7/22/25 | Fri 7/25/25 | | | | 1.2 | Open |
| 2 | Analysis Phase | Member 1 | 15 | Mon 7/28/25 | Fri 8/15/25 | | | | 1 | Open |
| 2.1 | Requirements gathering and owner interviews | Member 1 | 6 | Mon 7/28/25 | Mon 8/4/25 | | | | 1.3 | Open |
| 2.2 | Functional requirements and use case modeling | Member 1 | 5 | Tue 8/5/25 | Mon 8/11/25 | | | | 2.1 | Open |
| 2.3 | Nonfunctional requirements definition | Member 3 | 3 | Tue 8/5/25 | Thu 8/7/25 | | | | 2.1 | Open |
| 2.4 | Process modeling (Data Flow Diagrams) | Member 1 | 4 | Tue 8/12/25 | Fri 8/15/25 | | | | 2.2 | Open |
| 2.5 | Data modeling (Entity Relationship Diagram) | Member 2 | 4 | Tue 8/12/25 | Fri 8/15/25 | | | | 2.2 | Open |
| 3 | Design Phase | Member 2 | 16 | Mon 8/18/25 | Mon 9/8/25 | | | | 2 | Open |
| 3.1 | Database design (PostgreSQL + SQLite offline) | Member 2 | 8 | Mon 8/18/25 | Wed 8/27/25 | | | | 2.5 | Open |
| 3.2 | System and network architecture design | Member 2 | 6 | Mon 8/18/25 | Mon 8/25/25 | | | | 2.4 | Open |
| 3.3 | Desktop UI/UX design (PySide6) | Member 3 | 10 | Tue 8/26/25 | Mon 9/8/25 | | | | 3.2 | Open |
| 3.4 | Tablet kiosk UI design (PWA / APK) | Member 4 | 8 | Tue 8/26/25 | Thu 9/4/25 | | | | 3.2 | Open |
| 3.5 | Reports and document template design | Member 3 | 5 | Thu 8/28/25 | Wed 9/3/25 | | | | 3.1 | Open |
| 4 | Implementation Phase | Member 2 | 49 | Tue 9/9/25 | Fri 11/14/25 | | | | 3 | Open |
| 4.1 | Database and backend core setup | Member 2 | 6 | Tue 9/9/25 | Tue 9/16/25 | | | | 3.1 | Open |
| 4.2 | Booking and event calendar module | Member 2 | 10 | Wed 9/17/25 | Tue 9/30/25 | | | | 4.1 | Open |
| 4.3 | Customer management module | Member 1 | 6 | Wed 9/17/25 | Wed 9/24/25 | | | | 4.1 | Open |
| 4.4 | Menu package module | Member 3 | 8 | Wed 9/17/25 | Fri 9/26/25 | | | | 4.1 | Open |
| 4.5 | Billing and payment module | Member 2 | 10 | Wed 10/1/25 | Tue 10/14/25 | | | | 4.2, 4.4 | Open |
| 4.6 | Kitchen and inventory module | Member 3 | 8 | Mon 9/29/25 | Wed 10/8/25 | | | | 4.4 | Open |
| 4.7 | Tablet kiosk and LAN sync engine | Member 4 | 12 | Wed 10/1/25 | Thu 10/16/25 | | | | 4.2, 4.4 | Open |
| 4.8 | Reports and analytics dashboard | Member 1 | 8 | Wed 10/15/25 | Fri 10/24/25 | | | | 4.5 | Open |
| 4.9 | Testing (unit, integration, UAT) | Member 4 | 10 | Mon 10/27/25 | Fri 11/7/25 | | | | 4.7, 4.8 | Open |
| 4.10 | Deployment and installer packaging | Member 2 | 5 | Mon 11/10/25 | Fri 11/14/25 | | | | 4.9 | Open |

---

## 4. The Staffing Plan

An average of about four people are needed to deliver the system, which matches our four-member team. The roles required for the project are listed below, each assigned to a member according to their technical and interpersonal skills. Because the project is small, all team members report directly to the project manager, who also serves as a systems analyst.

| Role | Description | Assigned To |
| :--- | :--- | :--- |
| Project Manager / Systems Analyst | Oversees the project to ensure it meets its objectives on time and within budget; leads requirements gathering and analysis with the catering owner. | Member 1 |
| Database & Backend Developer (Technical Lead) | Designs and builds the PostgreSQL server and offline SQLite database, the LAN sync server, and the core application logic; oversees the technical work. | Member 2 |
| Desktop UI / Frontend Developer | Designs and codes the PySide6 desktop manager station — booking calendar, menu packages, and the reports/dashboard screens. | Member 3 |
| Tablet Kiosk Developer & QA Tester | Builds the Android tablet kiosk (PWA / APK) and the sync client, and leads unit, integration, and user-acceptance testing. | Member 4 |

**Reporting structure:** All project team members report to the Project Manager (Member 1).

```
                     Project Manager
                       (Member 1)
                           |
            +--------------+--------------+
            |                             |
      Functional Lead               Technical Lead
       (analysis / UI)                (Member 2)
            |                             |
   +--------+--------+           +--------+--------+
   |                 |           |                 |
 Desktop UI      QA / Kiosk    Database /      Kiosk & Sync
 (Member 3)      (Member 4)    Backend         (Member 4)
                               (Member 2)
```

**Special incentives:** Since finishing on schedule is important to the project's success, the team agreed that if the deadline is met, all members who contributed to the goal will be treated to a team dinner after the final defense. A small amount was also budgeted for snacks and drinks during long coding sessions.

---

## 5. Project Charter

**Project objective:** The Jayraldine's Catering project team will create a working desktop-and-tablet system that lets the business manage event reservations, menu packages, billing, and kitchen orders reliably, even without an internet connection.

The team members will:

1. Attend a team meeting every week to report the status of assigned tasks.
2. Update the work plan with actual dates and progress at the end of each week.
3. Discuss all problems with the project manager as soon as they are detected.
4. Support each other when help is needed, especially for tasks that could hold back the progress of the project.
5. Commit all working code to the shared repository and post important changes to the team group chat as they are made.

---

## 6. Key Milestones

| Milestone | Target Date |
| :--- | :---: |
| Approval of project proposal / system request | Thu 7/10/25 |
| Completion of feasibility study | Mon 7/21/25 |
| Sign-off of requirements (functional & nonfunctional) | Fri 8/15/25 |
| Completion of system & database design | Mon 9/8/25 |
| System prototype ready for review | Thu 10/16/25 |
| Start of user-acceptance testing (UAT) | Mon 10/27/25 |
| Final deployment and system turnover | Fri 11/14/25 |
