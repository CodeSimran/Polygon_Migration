# Issue Analysis & Edge Cases

## 3.1 Issue Identification

### Product Issues (User-Facing)

1. **Missing Async Progress Feedback (Priority: High)**
   - **Problem**: When fetching a problem with many test cases (e.g., 150+ tests), the Polygon API takes several seconds to respond. Currently, the UI simply freezes, and the browser looks like it's hanging.
   - **Impact**: Users might think the app crashed and refresh the page, sending duplicate expensive requests to the API. 
   - **Why Priority 1**: Bad user experience that directly leads to API rate-limiting and server overload. We need a loading spinner or a WebSocket progress bar.

2. **Hardcoded Testset Parameter (Priority: Medium)**
   - **Problem**: Polygon problems can have multiple testsets (e.g., `pretests` and `tests`). The app currently hardcodes the fetch to only grab `tests` or defaults to the first one it finds.
   - **Impact**: Problem setters who meticulously designed `pretests` will find that their pretests are completely ignored and not migrated to our platform.
   - **Why Priority 2**: This causes incomplete data migration, which is the core purpose of the tool.

3. **No Rollback on Partial Failures (Priority: Medium)**
   - **Problem**: If the user clicks "Migrate Test Cases to Cloud Storage" and it successfully uploads 15 test cases but fails on the 16th (due to network error), there is no rollback.
   - **Impact**: The cloud storage is left in an inconsistent state with partial files. 
   - **Why Priority 3**: The user has to click the button again, which overwrites the files, but it leaves "dirty" data if they decide to abort.

### Code Issues (Technical)

1. **Tight Coupling in Views / Fat Views (Priority: High)**
   - **Problem**: The `problems.views.index` function handles HTTP request parsing, cryptographic Polygon API signature generation, database ORM queries, and HTML rendering all in one massive function.
   - **Impact**: The code is incredibly difficult to unit test. You cannot test the Polygon API logic without mocking a full Django HTTP Request.
   - **Why Priority 1**: This architectural flaw makes the codebase unmaintainable and prone to regression bugs as the team scales. The API logic needs to be abstracted into a `PolygonClient` service class.

2. **In-Memory File Processing (Priority: High)**
   - **Problem**: When downloading test cases from Polygon and sending them to Cloud Storage, the app holds the entire string content of the test cases in RAM.
   - **Impact**: If a problem has 200MB of test cases (which is common for graphs/trees), the Django worker's RAM usage will spike. Multiple concurrent users will cause the server to crash with an Out-Of-Memory (OOM) error.
   - **Why Priority 2**: Major scalability bottleneck. The files should be streamed in chunks directly to the Storage Provider.

3. **Missing Unique Constraints & Error Handling (Priority: Medium)**
   - **Problem**: Database operations like `get_or_create` or `update` are used without wrapping them in proper `try/except` blocks for `IntegrityError`.
   - **Impact**: If bad data comes from Polygon (e.g., a missing required field or a duplicate slug), the app throws a 500 Server Error instead of catching it and showing a friendly UI message.
   - **Why Priority 3**: Poor error boundaries make debugging in production very painful.

---

## 3.2 Edge Case Analysis

**Q1: A Polygon problem has 0 sample test cases but 15 regular test cases. What happens when you migrate this problem?**
When migrated, the code checks the `useInStatements` flag from the Polygon API to determine if a test case is a sample. If there are 0 samples, the code will successfully migrate all 15 test cases, but the `is_sample` boolean in our database will simply be `False` for all of them. The migration will succeed, but the UI might look slightly bare because no "Sample" previews will be highlighted for the students.

**Q2: A problem is migrated with 20 test cases. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?**
Because the test case migration logic relies on `update_or_create` (using the test index), the first 12 test cases will be successfully updated with the new data. However, our database doesn't know about the deletions. Therefore, the remaining 8 test cases (indexes 13-20) will become "orphaned" and will remain in our database and cloud storage. The problem will incorrectly have 20 test cases on our platform instead of 12. To fix this, we should delete all existing test cases for the problem before running a fresh migration.

**Q3: Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?**
The system automatically generates a URL `slug` based on the problem title (e.g., `two-sum`). The Django database model likely enforces a `unique=True` constraint on the slug field to ensure URLs don't collide. When the second problem is migrated, the database will throw an `IntegrityError` because `two-sum` already exists, causing the app to crash with a 500 error. The slug generator needs a mechanism to append a random hash or the problem ID (e.g., `two-sum-69943`) to ensure uniqueness.

**Q4: When test cases are saved to the database via "Migrate Test Cases to DB", some data is intentionally discarded. What data is lost? Why might this cause problems?**
The actual massive strings containing the input/output data are intentionally discarded from the Postgres database to save space, keeping only the metadata (like `test_index` and `is_sample`). The raw data is meant to be sent to Cloud Storage instead. 
This can cause problems because we are splitting the source of truth across two disconnected systems (Database and Cloud Storage). If a developer runs the DB migration but forgets to run the Cloud Storage migration, the application thinks the test cases exist, but the actual files are missing, causing catastrophic crashes during code evaluation.
