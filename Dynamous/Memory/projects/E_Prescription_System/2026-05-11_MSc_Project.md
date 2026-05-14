---
type: project
project: E_Prescription_System
source_file: MSc_Project.pdf
date: 2026-05-11
tags: [project, E_Prescription_System]
---

# Enhancing E-Prescription Security Through QR-Code Enabled Digital Verification

## Summary
This MSc thesis proposes a web-based QR-code verification system designed to enhance the security of electronic prescription (e-prescription) systems in healthcare. E-prescriptions have become standard practice, improving clinical workflows and reducing medication errors, but they remain vulnerable to serious security threats including prescription fraud, data tampering, and unauthorized access. The system leverages cryptographic authentication, tamper detection, and standardized verification protocols to enable pharmacists to reliably verify prescription authenticity and prevent duplicate dispensing at the point of dispensing. By combining centralized database architecture with distributed QR-code-based verification, the system addresses critical interoperability gaps while maintaining practical accessibility for resource-limited healthcare settings. The proposed solution produces secure QR-encoded prescriptions with digital signatures and comprehensive audit trails, aiming to reduce prescription fraud and restore patient trust.

## Background / motivation
Recent investigations by the Drug Enforcement Administration found thousands of fake prescriptions created using stolen provider credentials, yet most existing e-prescription systems lack strong verification processes at the point of dispensing. While e-prescription technology has successfully optimized clinical workflows and reduced medication errors, existing research has focused predominantly on clinical decision support features while overlooking the urgent need for robust fraud prevention and verification mechanisms. Current systems are fragmented across different healthcare organizations with disparate IT systems that cannot easily communicate, creating both data integrity failures and security vulnerabilities. Pharmacies, as the final checkpoint to prevent fraudulent prescriptions from reaching patients, lack reliable tools to verify prescription authenticity, leaving the system dangerously vulnerable.

## Objectives
- Design and develop a module for QR-code generation that embeds prescription data with a digital signature from the prescriber
- Implement a robust verification protocol capable of authenticating the prescriber's identity and verifying data integrity of prescriptions, detecting any tampering, and preventing duplicate dispensing by invalidating prescriptions after first use
- Develop a standardized QR-encoding format that addresses interoperability issues and enables the system to function effectively without requiring deep integration into existing infrastructure
- Design an audit trail mechanism that securely and efficiently logs all prescription generation, verification, and dispensing events for accountability and fraud investigation support
- Evaluate the prototype's effectiveness against common scenarios to assess efficiency and scalability for use in various healthcare settings

## Scope
- In-scope: Web-based dual-interface system for prescribers and pharmacists; QR code generation and cryptographic encoding; pharmacy verification workflow; prescription status tracking and invalidation; audit logging of all prescription events; camera-based and file-upload QR scanning
- Future work (out-of-scope): Full Electronic Health Record (EHR) and Hospital Information System (HIS) integration; native mobile applications for iOS/Android; blockchain-based decentralized audit trails; formal standardization submission to HL7/FHIR organizations

## Deliverables
- Functional prototype of web-based QR-code enabled prescription verification system
- Prescriber web interface for secure prescription generation and QR code creation
- Pharmacist web interface for QR scanning and prescription verification
- QR-code generation module with embedded cryptographic signatures
- Prescription verification and authentication protocol implementation
- Audit trail logging system with immutable event records
- System documentation and architecture specifications
- Test scenarios and evaluation results demonstrating fraud prevention effectiveness

## Methodology / approach

### System Architecture Overview
The proposed system implements a dual-interface architecture enabling secure prescription generation, transmission, and verification between prescribers and pharmacists. It employs a hybrid approach combining centralized database architecture for efficient prescription storage with distributed verification capabilities through QR codes. Each prescription undergoes a multi-stage lifecycle: generation by authorized prescribers, encoding into secure QR codes, patient-mediated transmission, pharmacy-based verification, and dispensing with comprehensive audit logging. This approach maintains digital security and traceability while providing patients with tangible prescription documents, addressing the primary non-adherence rates of 22-28% identified in literature.

### Prescription Generation and QR Encoding
The doctor-side workflow begins with secure login and authentication. Upon successful authentication, prescribers access a structured prescription form enforcing mandatory fields including patient demographics, medication details, dosage instructions, and validity period. The system generates a unique prescription identifier (UUID v4) for each prescription, effectively eliminating collision probability. This identifier, combined with prescription metadata, undergoes cryptographic hashing (SHA-256) to create a verification fingerprint embedded within the QR code. The complete prescription record is atomically written to the database with ACID transaction guarantees, ensuring data consistency even under system failures. Following successful database insertion, the system initiates QR-code generation encoding the prescription ID and verification hash, embedded into a prescription template containing human-readable information including medication name, dosage, prescriber details, and prescription validity. The system provides dual output options: direct printing for paper prescriptions and digital transmission via hospital portal.

### Pharmacy Verification and Dispensing
The pharmacist interface implements a streamlined verification process optimized for high-volume dispensing environments. Upon QR code scanning, the system extracts the embedded prescription identifier and verification hash. The decoder implements multiple image preprocessing techniques to ensure successful QR recognition under suboptimal lighting or image quality conditions, supporting both camera-based real-time scanning using WebRTC APIs and file upload for pre-captured QR images. The dispensing confirmation process implements a two-step verification requiring explicit pharmacist acknowledgment before marking prescriptions as dispensed. The system then updates the prescription status while creating immutable audit log entries recording timestamp, pharmacist identifier, and pharmacy location. This prevents duplicate dispensing and provides comprehensive audit trails for fraud investigation support.

### Security Implementation
Digital signatures employ RSA-2048 with PKCS#1 v1.5 padding for prescription integrity verification. Sensitive patient and prescription data are protected using AES-256 encryption. Cryptographic operations utilize the Web Crypto API for password hashing, ensuring resistance against rainbow table attacks. All network communications are secured with HTTPS, preventing man-in-the-middle attacks. Database schema implements normalized tables with foreign key constraints and automatic triggers for audit trail maintenance. The QR code acts as both a verification token and an information carrier, enabling offline verification capabilities when necessary while preventing prescription tampering.

### Interface Design
The prescriber web interface implements task-oriented design minimizing cognitive load during prescription creation, guiding prescribers through patient selection, medication choice, dosage calculation, and prescription review before final submission. The responsive design adapts to various screen sizes from desktop workstations to tablet devices used in clinical rounds, with real-time validation providing immediate feedback on data entry errors. The pharmacist interface prioritizes efficiency and accuracy for high-volume prescription processing, with the QR scanning interface providing visual feedback confirming successful code capture. The prescription detail view presents database information alongside scanned prescription images, enabling visual verification of prescription authenticity.

## Tech stack
- Node.js — backend server-side implementation with event-driven, non-blocking I/O model for handling concurrent prescription requests
- MySQL — relational database management system for storing prescription records, user credentials, and audit logs
- AES-256 — encryption standard for protecting sensitive patient and prescription data
- qrcode.js — library for QR code generation
- ZXing (Zebra Crossing) — library for robust QR code scanning and decoding across various image conditions
- WebRTC — protocol enabling camera-based real-time QR scanning capabilities
- Web Crypto API — implementation of cryptographic operations including password hashing
- RSA-2048 with PKCS#1 v1.5 — digital signature algorithm for prescription integrity verification
- HTTPS — encrypted network communication protocol preventing man-in-the-middle attacks
- React.js — frontend JavaScript framework for building responsive single-page web applications
- CSS — styling for responsive web interface design
- UUID v4 — generation of unique prescription identifiers
- SHA-256 — cryptographic hash algorithm for creating verification fingerprints

## Key dates
- 2025-02-00: Project submitted (February 2025)
- 2025-11-00: Project approved and certified (November 2025)
- Phase timeline (6 months, 25 weeks total):
  - Weeks 1–5: Define Scope
  - Weeks 4–8: System Architecture Design
  - Weeks 7–14: Backend Development (database and cryptographic module)
  - Weeks 10–16: Frontend Development (responsive user interface)
  - Weeks 15–17: System Integration (frontend to backend)
  - Weeks 16–21: Testing & Evaluation (unit tests and test scenario simulation)

## Stakeholders / team
- Md Shamse Kadir Khan: Student researcher (Exam Roll: 240116)
- Dr. M. Shamim Kaiser: Supervisor, Professor at Institute of Information Technology
- Dr. Jesmin Akhter: Committee Chairman
- Dr. M Mesbahuddin Sarker: Committee Member
- Mehrin Anannya: Committee Member
- Prof. Dr. Md Saiful Islam: External Committee Member
- Institute of Information Technology, Jahangirnagar University
- Target users: Prescribers (physicians), Pharmacists, Patients

## Risks / open items
- System success depends on adequate web infrastructure and consistent internet access in pharmacy settings
- User adoption and effectiveness require adequate technical skill among prescribers and pharmacists
- Integration with existing fragmented EHR/HIS systems remains a challenge requiring future development
- Formal standardization through HL7/FHIR organizations needed for true interoperability at scale
- Decentralized blockchain alternative to centralized audit logging requires future exploration

## Notable details

### Key Findings from Literature Review
- Multiple e-prescription system architectures exist across eight countries (Canada, US, UK, Australia, Spain, Japan, Sweden, Denmark) with significant differences in centralized vs. distributed models
- Observational studies in community pharmacies found "technology incompatibility between pharmacy and clinic systems" as primary contributor to errors including wrong drug quantity and dosing directions
- Analysis of 195,930 e-prescriptions revealed significant percentage of prescriptions never filled, indicating "open-loop flaw" with no confirmation mechanism for final dispensing status
- Study found that internally developed low-cost systems effectively reduced clinical errors but significantly increased duplication errors without robust invalidation mechanisms
- Qualitative research revealed patients appreciate convenience but report loss of control, anxiety about misdirected prescriptions, and reduced communication with "black box" nature of e-prescriptions
- Physician perception study in resource-limited setting found 58.07% paper-based error rate but identified practical success factors: good internet access and technical skill of users
- Proposed smart-card security solutions validated need for cryptographic signing but proved cost-prohibitive and infrastructure-intensive

### Critical System Vulnerabilities Addressed
- "Last Mile" vulnerability: Most critical weakness is lack of secure, standardized verification protocol at point of dispensing where prescriptions are actually dispensed
- Open-loop systems: Effective at sending prescriptions but have no reliable mechanism to confirm authenticity, integrity, or dispensing status
- Data integrity failures: Lack of standardization between clinic and pharmacy systems causes active data corruption during transfer
- Prescription duplication: Basic e-prescription systems without closed-loop invalidation mechanism lead to significant increase in duplication errors
- Weak prescriber authentication: Most systems lack reliable method for pharmacist to verify prescriber identity and prescription authenticity

### Design Principles
- Low-cost, web-based approach requiring minimal technical skill to maximize adoption, especially in resource-limited settings
- Standardized QR-encoding format to bypass fragile point-to-point integrations between incompatible systems
- Patient-centric design integrating security with user experience transparency
- Dual verification step requiring explicit pharmacist acknowledgment before marking prescriptions dispensed
- ACID transaction guarantees ensuring data consistency even under system failures
- Offline verification capabilities through QR codes enabling operation in environments with intermittent connectivity

### Expected Outcomes
- Noticeable reduction in prescription fraud through robust verification at point of dispensing
- Efficient prescription verification without requiring deep integration into existing healthcare IT infrastructure
- Scalable framework compatible with various healthcare settings and organizational structures
- Enhanced patient trust through transparent, participatory verification process
- Comprehensive audit trails supporting fraud investigations and regulatory compliance