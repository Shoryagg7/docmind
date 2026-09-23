"""Golden set. `evidence` is text that must appear in a retrieved chunk (None when
the question is unanswerable). `needs_consent` marks questions the privacy policy must
flag. The eval then re-asks them with consent so every item still gets an answer."""

GOLDEN_SET = [
    # sample.pdf: Maya Chen bio (12 answerable)
    {
        "question": "What city does Maya Chen work in?",
        "source": "sample.pdf",
        "reference_answer": "Toronto",
        "evidence": "backend engineer based in\nToronto",
    },
    {
        "question": "What city was Maya Chen born in?",
        "source": "sample.pdf",
        "reference_answer": "Vancouver",
        "evidence": "I was born in Vancouver",
    },
    {
        "question": "What year did Maya Chen move to Toronto?",
        "source": "sample.pdf",
        "reference_answer": "2019",
        "evidence": "moved to Toronto in 2019",
    },
    {
        "question": "What university did Maya Chen graduate from?",
        "source": "sample.pdf",
        "reference_answer": "University of Waterloo",
        "evidence": "graduated from the University of Waterloo",
    },
    {
        "question": "What company does Maya Chen currently work for?",
        "source": "sample.pdf",
        "reference_answer": "Northwind Analytics",
        "evidence": "Senior Backend Engineer at Northwind Analytics",
    },
    {
        "question": "What is Maya Chen's current job title?",
        "source": "sample.pdf",
        "reference_answer": "Senior Backend Engineer",
        "evidence": "Senior Backend Engineer at Northwind Analytics",
    },
    {
        "question": "What company did Maya Chen work at before her current job?",
        "source": "sample.pdf",
        "reference_answer": "Bluefin Logistics",
        "evidence": "Software Engineer at Bluefin Logistics",
    },
    {
        "question": "What was the name of the fintech company where Maya Chen had her first job?",
        "source": "sample.pdf",
        "reference_answer": "Ledgerly",
        "evidence": "called Ledgerly",
    },
    {
        "question": "What technologies were used to build RiverStream?",
        "source": "sample.pdf",
        "reference_answer": "Kafka and Flink",
        "evidence": "built with Kafka and Flink",
    },
    {
        "question": "What programming language is CoralCache written in?",
        "source": "sample.pdf",
        "reference_answer": "Go",
        "evidence": "written in Go",
    },
    {
        "question": "What does TidalMap do?",
        "source": "sample.pdf",
        "reference_answer": "It's an open source geospatial routing library.",
        "evidence": "TidalMap, an open source geospatial routing library",
    },
    {
        "question": "What instrument does Maya Chen play?",
        "source": "sample.pdf",
        "reference_answer": "Violin",
        "evidence": "playing the violin",
    },
    # sample2.pdf: Nimbus Cloud Storage product doc (10 answerable)
    {
        "question": "How much does the Starter tier cost per month?",
        "source": "sample2.pdf",
        "reference_answer": "5 dollars per month",
        "evidence": "The Starter tier costs 5 dollars",
    },
    {
        "question": "How many gigabytes of storage does the Starter tier include?",
        "source": "sample2.pdf",
        "reference_answer": "50 gigabytes",
        "evidence": "includes 50 gigabytes of storage",
    },
    {
        "question": "How much does the Pro tier cost per month?",
        "source": "sample2.pdf",
        "reference_answer": "15 dollars per month",
        "evidence": "The Pro tier costs 15 dollars per month",
    },
    {
        "question": "How many gigabytes of storage does the Pro tier include?",
        "source": "sample2.pdf",
        "reference_answer": "500 gigabytes",
        "evidence": "includes 500 gigabytes of storage",
    },
    {
        "question": "What kind of support does the Pro tier include?",
        "source": "sample2.pdf",
        "reference_answer": "Priority email support",
        "evidence": "priority email support",
    },
    {
        "question": "What uptime SLA does the Enterprise tier guarantee?",
        "source": "sample2.pdf",
        "reference_answer": "99.99 percent",
        "evidence": "99.99 percent uptime SLA",
    },
    {
        "question": "Within how many days can Starter and Pro customers request a refund?",
        "source": "sample2.pdf",
        "reference_answer": "14 days",
        "evidence": "full refund within 14 days",
    },
    {
        "question": "How long are deleted files kept in the recovery bin before permanent deletion?",
        "source": "sample2.pdf",
        "reference_answer": "30 days",
        "evidence": "retained for 30 days before",
    },
    {
        "question": "How long is account data for cancelled subscriptions retained?",
        "source": "sample2.pdf",
        "reference_answer": "90 days",
        "evidence": "retained for 90 days",
    },
    {
        "question": "What encryption is used to protect data at rest?",
        "source": "sample2.pdf",
        "reference_answer": "AES-256",
        "evidence": "encrypted at rest using AES-256",
    },
    # Unanswerable (3): grounding should refuse, not guess
    {
        "question": "What is the capital of France?",
        "source": "sample.pdf",
        "reference_answer": "Not answerable — the document is a bio, not a geography reference.",
        "evidence": None,
    },
    {
        "question": "What city does Maya Chen work in?",
        "source": "sample2.pdf",
        "reference_answer": "Not answerable — sample2.pdf is a product doc and never mentions Maya Chen.",
        "evidence": None,
    },
    {
        "question": "What is the boiling point of water in Celsius?",
        "source": None,
        "reference_answer": "Not answerable — neither uploaded document covers this topic.",
        "evidence": None,
    },
    # synthetic_pii.pdf: fictional employee record (3 lookups, 2 consent, 1 unanswerable)
    {
        "question": "What is Ananya Kulkarni's work email address?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "ananya.kulkarni@tamarind.example",
        "evidence": "Work email: ananya.kulkarni@tamarind.example",
    },
    {
        "question": "Who is Ananya Kulkarni's manager?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "Rohan Deshpande",
        "evidence": "Her manager is Rohan Deshpande",
    },
    {
        "question": "What is the mobile number of Ananya Kulkarni's emergency contact?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "+91 90000 00002 (her sister, Meera Kulkarni)",
        "evidence": "mobile +91 90000 00002",
    },
    {
        "question": "Is Ananya Kulkarni's personal email address on the example.com domain?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "Yes (ananya.k@example.com)",
        "evidence": "Personal email: ananya.k@example.com",
        "needs_consent": True,
    },
    {
        "question": "Does Ananya Kulkarni's PAN start with the letters ABC?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "Yes (ABCPK1234Z)",
        "evidence": "PAN: ABCPK1234Z",
        "needs_consent": True,
    },
    {
        "question": "What is Ananya Kulkarni's passport number?",
        "source": "synthetic_pii.pdf",
        "reference_answer": "Not answerable — the record has no passport number.",
        "evidence": None,
    },
]
