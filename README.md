# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section _after_ you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

Course and professor reviews at the University of Maryland, College Park

---

## Document Sources

| #   | Source                              | Type                                                                                                    | URL or file path                                                                               |
| --- | ----------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| 1   | PlanetTerp API                      | Planet terp is a website with lots of course and professor reviews for the University of Maryland (UMD) | https://planetterp.com/api/                                                                    |
| 2   | UMD Office of Undergraduate Studies | Official class catalog for 2026-2027                                                                    | https://academiccatalog.umd.edu/undergraduate/approved-courses                                 |
| 3   | UMD Office of Undergraduate Studies | General Education Requirements                                                                          | https://gened.umd.edu/sites/default/files/2024-04/GenEdFolder24-25.pdf                         |
| 4   | University of Maryland              | Schedule of Classes                                                                                     | https://app.testudo.umd.edu/soc/gen-ed/                                                        |
| 5   | Reddit                              | Computer Science Course Recommendations                                                                 | https://www.reddit.com/r/UMD/comments/wi60h9/cmsc_courses_post_graduation_review_and_some/     |
| 6   | Reddit                              | Weed Out Courses at UMD                                                                                 | https://www.reddit.com/r/UMD/comments/1kjoatw/weeded_out                                       |
| 7   | Reddit                              | Course Evaluations at UMD                                                                               | https://www.reddit.com/r/UMD/comments/1h5tidr/im_begging_yall_to_fill_out_course_evals_closing |
| 8   | UMD IO                              | Non-live data about UMD (buildings, facilities, etc.)                                                   | https://github.com/umdio/umdio-data                                                            |
| 9   | UMD IO                              | Live data about UMD (professors, courses, buses, etc.)                                                  | https://beta.umd.io/                                                                           |
| 10  | Reddit                              | Premed Class Recommendations at UMD                                                                     | https://www.reddit.com/r/UMD/comments/1pyfk8z/pre_med_classes_at_umd/                          |

---

## Chunking Strategy

**Chunk size:**
300-400 tokens

**Overlap:**
50 tokens

**Why these choices fit your documents:**'
The information I will get from PlanetTerp reviews and Reddit comments are likely to be short. I think that 300-400 tokens should be enough to capture them completely. 50 tokens should be enough to handle overlap.

**Final chunk count:**
16330 chunks (it sounds like a lot but its mostly from the PlanetTerp API).

---

## Embedding Model

**Model used:**
I will be using all-MiniLM-L6-v2 via sentence-transformers.

**Production tradeoff reflection:**
The main tradeoffs to weigh in choosing a different embedding model would be domain accuracy with UMD specific information like course codes and latency because higher dimension embeddings are more accurate but take more time than lower dimension embeddings.

---

## Grounded Generation

**System prompt grounding instruction:**
The system prompt fives the model five rules it cannot break to enforce some of the requirements of this project. The instruction given is to answer the query only using information from the documents section. Avoid using training knowledge, general facts, or outside knowledge. If the documents don't contain enough information then respond by saying "I don't have enough information on that." The retrieved chunks are injected into the user's message under a Documents header so that the model can use that as context.

**How source attribution is surfaced in the response:**
The source attribution is done programmatically in the build_sources function in the generate.py file. The chunk metadata is used from the vector databased in order to get citations. For each retrieved chunk, the function gets the professor name, course, and PlanetTerp URL and then returns a list that the UI displays. The LLM's text and the source list are produced independently and then combined making attribution guaranteed even if the model's answer contains no citations at all.

---

## Evaluation Report

| #   | Question                                                                        | Expected answer                                                                                                                                         | System response (summarized)                                                                                                                                                                                                                                                                   | Retrieval quality | Response accuracy |
| --- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ----------------- |
| 1   | Who is the best professor for CMSC131?                                          | Nelson Padua-Perez is the best professor for CMSC131 as he has high reviews on PlanetTerp.                                                              | According to the documents, there are two professors with a 5/5 rating for CMSC131: Fawzi Emad and William Pugh. One student describes Fawzi Emad as "the best professor I've ever had" (Doc 1), while another student highly recommends William Pugh if you "have a little coding background" | Relevant          | accurate          |
| 2   | What is the average grade for students in Algorithms (CMSC351)?                 | According to PlanetTerp, the average GPA for students in CMSC351 is between 50-60 Many students consider this course to be a difficult weed out course. | The average grade for CMSC351 is 56.6.                                                                                                                                                                                                                                                         | Relevant          | accurate          |
| 3   | What Distributive Studies Gen Ed categories do UMD undergrads have to complete? | UMD undergrads must complete five categories of Gen Eds: DSSP, DSHU, DSNS, DSNL, and DSBS. This is according to UMD's Gen Ed Guide.                     | According to the documents, UMD undergrads have to complete the following Distributive Studies Gen Ed categories:                                                                                                                                                                              |

1. Natural Sciences (with one course including a laboratory experience)
2. History and Social Sciences
3. Humanities
4. Two Big Question (formerly I-Series) courses
5. Two Scholarship in Practice courses (with one outside the student's major requirements). | Relevant | accurate |
   | 4 | What computer science professors should I avoid taking? | According to PlanetTerp, Professor Larry Herman has negative reviews for many of the classes he teaches. | Based on the documents, you should consider avoiding Professor Larry Herman, as he has a rating of 1/5 for CMSC132 in Doc 3, with a student comment that advises not to take a class with him. However, it's worth noting that in Doc 5, he received a rating of 4/5 for the same course, CMSC132, which provides a more positive assessment. | Relevant | accurate |
   | 5 | What is the distributive studies gen ed requirement? | Distributive studies is a gen ed requirement that teches students about a variety of disciplines, the methods they use, the kinds of questions they ask, and their standards for judging the answers. | According to Doc 1 and Doc 5, the Distributive Studies gen ed requirement is that students must complete a minimum of 8 DS courses, with 2 courses in each area, and one of the Natural Sciences courses must include a laboratory experience. Additionally, 2 of the 8 courses must be Big Question (formerly "I-Series") courses. | Relevant | accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:**
What is INST326 like and who teaches it?

**What the system returned:**
A mixed answer with details from INST123 and INST326 reviews that both taught by Christopher Dempwolf. The model described INST326 as "a bit disorganized at times," a phrase that appears in INST123/INST126 reviews, not the INST326 review.

**Root cause (tied to a specific pipeline stage):**
This is likely due to retrieval ranking failure. INST326 in the query maps to a general "INST-family course about information science" vector rather than pinpointing the specific course number. INST123 reviews by the same professor landed closer in embedding space than the actual INST326 review.

**What you would change to fix it:**
Add a course-number metadata filter at query time (where={"course": "INST326"}), which would isolate only the actual INST326 review and eliminate the cross-course blending entirely.

---

## Spec Reflection

**One way the spec helped you during implementation:**
The spec helped me during the implementation because it was something that I could go back to check what resources I was using or how I was structuring the project. I think that taking the time to write out the spec focument was helpful for me and Claude Code because then Claude had a clear idea of what I was trying to do.

**One way your implementation diverged from the spec, and why:**
One way my implementation diverged from the spec was that I was not expecting to have so many chunks. This was because the PlanetTerpAPI was a lot of chunks. This caused some issues down the line in pipelining that took some time to fix.

---

## AI Usage

**Instance 1**

- _What I gave the AI:_
  I gave the AI the structure of how I wanted it to implement the embedding and storing step. I reminded it to refer the relevant sections in planning.md and I asked it run tests to determine if the code it had written was working as intended afterward.
- _What it produced:_
  It produced the embed.py file.
- _What I changed or overrode:_
  Like I mentioned above there were some issues with the pipelining of the embedding chunks into the database. I had to adjust how the information from the sources was being scraped/chunked to avoid some errors that kept happening.

**Instance 2**

- _What I gave the AI:_
  I prompted the AI to help code the logic for chunking and building the document pipeline in general. I gave it an explanation of the pipeline structure I wanted. I asked it to clean the documents according to the instructions given.
- _What it produced:_
  It produced the chunker.py file
- _What I changed or overrode:_
  There was a small issue with cleaning the chunks because some of them were being stored with irrelevant or messed up text. I discovered this when I was verifying the output by sampling random chunks. I fixed this and the outputs looked much better.
