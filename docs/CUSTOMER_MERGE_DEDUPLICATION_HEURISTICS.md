# Customer Deduplication & Levenshtein Name Distance Heuristics

## 1. Matching Heuristics
When new customer orders arrive from tablet kiosks, deduplication checks evaluate:

1. **Exact Phone Match**: Normalized 10-11 digit phone number match.
2. **Fuzzy Name Similarity**: Levenshtein distance ratio $\ge 0.85$ on normalized customer names.
3. **Address Proximity**: Matching barangay and municipality coordinates.
