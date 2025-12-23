# GitHub Star Crawler - Complete Technical Assessment Guide

## Table of Contents
1. [Understanding the Assignment](#understanding-the-assignment)
2. [Project Overview](#project-overview)
3. [Architecture & Design](#architecture--design)
4. [Prerequisites & Installation](#prerequisites--installation)
5. [Running the Project](#running-the-project)
6. [GitHub Actions CI/CD Pipeline](#github-actions-cicd-pipeline)
7. [Database Schema & Design](#database-schema--design)
8. [API Rate Limiting & Retry Logic](#api-rate-limiting--retry-logic)
9. [Scaling Considerations](#scaling-considerations)
10. [Future Schema Evolution](#future-schema-evolution)
11. [Performance Optimization](#performance-optimization)

---

## Understanding the Assignment

### What We're Building

This is a **GitHub Repository Crawler** that:
1. Uses GitHub's GraphQL API to fetch data about repositories
2. Collects star counts and metadata for 100,000 GitHub repositories
3. Stores this data efficiently in PostgreSQL
4. Runs continuously (designed for daily execution via GitHub Actions)
5. Exports data to CSV and JSON formats

### Key Requirements

| Requirement | What It Means | Why It Matters |
|---|---|---|
| **100,000 repos** | Fetch star data from 100k GitHub repositories | Testing scalability and API efficiency |
| **Rate Limiting** | GitHub limits API calls to 5,000 points/hour | Must respect limits or risk being blocked |
| **Retry Mechanisms** | Automatically retry failed requests | Network issues are common; must be resilient |
| **PostgreSQL Database** | Store data in relational database | For efficient querying and historical tracking |
| **Efficient Updates** | Minimal database changes when re-crawling | Crawling daily means many updates |
| **GitHub Actions** | Automated pipeline in CI/CD | Zero-trust deployment; no private secrets |
| **Code Quality** | Clean architecture, separation of concerns | Required for professional engineering |

---

## Project Overview

### What This Project Does
