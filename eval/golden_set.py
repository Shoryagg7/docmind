GOLDEN_SET = [
    # sample.pdf — Maya Chen bio (12 answerable questions)
    {
        "question": "What city does Maya Chen work in?",
        "source": "sample.pdf",
        "reference_answer": "Toronto",
    },
    {
        "question": "What city was Maya Chen born in?",
        "source": "sample.pdf",
        "reference_answer": "Vancouver",
    },
    {
        "question": "What year did Maya Chen move to Toronto?",
        "source": "sample.pdf",
        "reference_answer": "2019",
    },
    {
        "question": "What university did Maya Chen graduate from?",
        "source": "sample.pdf",
        "reference_answer": "University of Waterloo",
    },
    {
        "question": "What company does Maya Chen currently work for?",
        "source": "sample.pdf",
        "reference_answer": "Northwind Analytics",
    },
    {
        "question": "What is Maya Chen's current job title?",
        "source": "sample.pdf",
        "reference_answer": "Senior Backend Engineer",
    },
    {
        "question": "What company did Maya Chen work at before her current job?",
        "source": "sample.pdf",
        "reference_answer": "Bluefin Logistics",
    },
    {
        "question": "What was the name of the fintech company where Maya Chen had her first job?",
        "source": "sample.pdf",
        "reference_answer": "Ledgerly",
    },
    {
        "question": "What technologies were used to build RiverStream?",
        "source": "sample.pdf",
        "reference_answer": "Kafka and Flink",
    },
    {
        "question": "What programming language is CoralCache written in?",
        "source": "sample.pdf",
        "reference_answer": "Go",
    },
    {
        "question": "What does TidalMap do?",
        "source": "sample.pdf",
        "reference_answer": "It's an open source geospatial routing library.",
    },
    {
        "question": "What instrument does Maya Chen play?",
        "source": "sample.pdf",
        "reference_answer": "Violin",
    },
    # sample2.pdf — Nimbus Cloud Storage product doc (10 answerable questions)
    {
        "question": "How much does the Starter tier cost per month?",
        "source": "sample2.pdf",
        "reference_answer": "5 dollars per month",
    },
    {
        "question": "How many gigabytes of storage does the Starter tier include?",
        "source": "sample2.pdf",
        "reference_answer": "50 gigabytes",
    },
    {
        "question": "How much does the Pro tier cost per month?",
        "source": "sample2.pdf",
        "reference_answer": "15 dollars per month",
    },
    {
        "question": "How many gigabytes of storage does the Pro tier include?",
        "source": "sample2.pdf",
        "reference_answer": "500 gigabytes",
    },
    {
        "question": "What kind of support does the Pro tier include?",
        "source": "sample2.pdf",
        "reference_answer": "Priority email support",
    },
    {
        "question": "What uptime SLA does the Enterprise tier guarantee?",
        "source": "sample2.pdf",
        "reference_answer": "99.99 percent",
    },
    {
        "question": "Within how many days can Starter and Pro customers request a refund?",
        "source": "sample2.pdf",
        "reference_answer": "14 days",
    },
    {
        "question": "How long are deleted files kept in the recovery bin before permanent deletion?",
        "source": "sample2.pdf",
        "reference_answer": "30 days",
    },
    {
        "question": "How long is account data for cancelled subscriptions retained?",
        "source": "sample2.pdf",
        "reference_answer": "90 days",
    },
    {
        "question": "What encryption is used to protect data at rest?",
        "source": "sample2.pdf",
        "reference_answer": "AES-256",
    },
    # Unanswerable cases (3) — grounding should refuse, not guess
    {
        "question": "What is the capital of France?",
        "source": "sample.pdf",
        "reference_answer": "Not answerable — the document is a bio, not a geography reference.",
    },
    {
        "question": "What city does Maya Chen work in?",
        "source": "sample2.pdf",
        "reference_answer": "Not answerable — sample2.pdf is a product doc and never mentions Maya Chen.",
    },
    {
        "question": "What is the boiling point of water in Celsius?",
        "source": None,
        "reference_answer": "Not answerable — neither uploaded document covers this topic.",
    },
]
