# Overview

## Current Behavior

The Uploaded documents table exposes processing status and update time, but does not summarize the
document or offer a delete action. Opening the document is labelled as a generic open action even
though the destination is the existing editor.

## Target Behavior

The table presents Document, Summary, Size, and Actions. Researchers can open the existing editor;
owners can confirm deletion of an inactive document that is not protected by intake or applied-graph
provenance.

## Affected Users

- Viewers browsing uploaded documents.
- Researchers editing uploaded documents.
- Owners deleting uploaded documents.

## Affected Product Docs

- `Docs/Research System Implementation Plan.md`
- `Docs/Business AI Agents Graph Intelligence Upgrade Plan.md`

## Non-Goals

- AI-generated abstractive summaries at list-query time.
- Deleting canonical graph knowledge created from an applied change set.
- Bulk document deletion.
