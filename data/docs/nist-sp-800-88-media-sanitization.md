---
title: NIST SP 800-88 - Guidelines for Media Sanitization
publisher: NIST
url: https://csrc.nist.gov/pubs/sp/800/88/r2/final
note: Starter summary written for this project in plain language. Verify against the official publication before relying on it.
---

# Media Sanitization (NIST SP 800-88)

## What media sanitization means
Media sanitization is the process of making data on storage media, such as hard drives, solid-state drives, USB drives, phones, and paper, unrecoverable before the media is reused, recycled, or thrown away. Simply deleting files or emptying the trash does not remove the underlying data.

## Clear
Clear uses logical techniques, such as overwriting all user-addressable storage with new values, to protect against simple, non-invasive data recovery. Clearing is appropriate when media will be reused within the organization at the same security level.

## Purge
Purge uses physical or logical techniques that make data recovery infeasible even with state-of-the-art laboratory methods. Examples include cryptographic erase, block erase commands built into solid-state drives, and degaussing magnetic media. Purging is appropriate when media holding sensitive data will leave the organization's control.

## Destroy
Destroy makes data recovery infeasible and also makes the media unusable for storing data. Methods include shredding, disintegrating, pulverizing, and incinerating. Destruction is appropriate for highly sensitive data or for media that cannot be reliably purged.

## Choosing a sanitization method
The right method depends on the confidentiality level of the data, the type of media, and whether the media will be reused inside the organization or leave its control. Higher sensitivity and media leaving the organization call for stronger methods.

## Verifying and documenting sanitization
Organizations should verify that sanitization worked and keep a record of it, such as a certificate of sanitization that lists the media, the method used, the date, and the person who performed it.

## Disposing of old devices and paper records
Employees should never throw devices or documents containing sensitive information in the regular trash or recycling. Old laptops, drives, and phones should be returned to IT for sanitization, and sensitive paper documents should be shredded or placed in secure disposal bins.
