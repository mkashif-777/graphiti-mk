import pandas as pd

# Data from files
group_id = "120363028475123456@g.us"

qa_data = [
    # 1. Factoid
    [1, "Factoid / Single-Hop", "What is the primary display title of the group?", "text", "Ancient Civilizations Study Group", group_id, "17025551001", "wamid.event_001"],
    [2, "Factoid / Single-Hop", "What is the name of the user with phone number ID 17025551001?", "text", "Sarah Martinez", group_id, "17025551001", "wamid.event_001"],
    [3, "Factoid / Single-Hop", "Who sent the message 'Welcome everyone! Let's start our discussion...'?", "text", "Sarah Martinez", group_id, "17025551001", "wamid.event_004"],
    [4, "Factoid / Single-Hop", "What was the very first system message event in the chat history?", "text", "group_title_changed", group_id, "17025551001", "wamid.event_001"],
    [5, "Factoid / Single-Hop", "Which user has the ID 17025551005?", "text", "Lisa Anderson", group_id, "17025551005", ""],
    
    # 2. Multi-Hop
    [6, "Multi-Hop", "Who replied to Sarah's initial message about the Roman administrative systems?", "text", "David Chen", group_id, "17025551002", "wamid.event_005"],
    [7, "Multi-Hop", "Who replied to David Chen's message about Roman road networks?", "text", "Emma Thompson", group_id, "17025551003", "wamid.event_006"],
    [8, "Multi-Hop", "Who reacted to Sarah Martinez's photo of the Roman Colosseum with a 🏛️ emoji?", "text", "Michael Rodriguez", group_id, "17025551004", "wamid.event_013"],
    [9, "Multi-Hop", "Which user replied to Emma Thompson's point about Marcus Aurelius and Stoic philosophy?", "text", "David Chen", group_id, "17025551002", "wamid.event_016"],
    [10, "Multi-Hop", "Who responded to Michael Rodriguez's video about pyramid construction?", "text", "Lisa Anderson", group_id, "17025551005", "wamid.event_020"],
    
    # 3. Multi-Modal
    [11, "Multi-Modal Retrieval", "What is the filename of the research paper shared by David Chen regarding Roman administration?", "text", "roman_empire_administration_research.pdf", group_id, "17025551002", "wamid.event_012"],
    [12, "Multi-Modal Retrieval", "What was the caption of the image shared by Michael Rodriguez at timestamp 1735478550?", "text", "The Roman Colosseum at sunset. Truly a marvel of architecture.", group_id, "17025551004", "wamid.event_010"],
    [13, "Multi-Modal Retrieval", "What file did Michael Rodriguez share related to cuneiform translation?", "text", "cuneiform_translation_guide.pdf", group_id, "17025551004", "wamid.event_043"],
    [14, "Multi-Modal Retrieval", "Identify the emoji used by Sarah to react to the Byzantine military tactics document.", "text", "💯", group_id, "17025551001", "wamid.event_027"],
    [15, "Multi-Modal Retrieval", "What is the filename of the document shared by Sarah Martinez near the end of the first transcript?", "text", "ancient_rome_timeline.pdf", group_id, "17025551001", "wamid.event_062"],
    
    # 4. Temporal
    [16, "Temporal / Sequence", "What was the last text message sent in the chat history?", "text", "This has been an incredible discussion everyone!", group_id, "17025551004", "wamid.event_064"],
    [17, "Temporal / Sequence", "Who was the second person to join the group?", "text", "David Chen", group_id, "17025551002", "wamid.event_002"],
    [18, "Temporal / Sequence", "What was discussed immediately after David Chen shared the Byzantine military document?", "text", "Sarah reacted with 💯 and Emma joined the discussion about the Byzantine Empire.", group_id, "17025551001;17025551003", "wamid.event_027;wamid.event_028"],
    [19, "Temporal / Sequence", "When did the group title change to 'Ancient Civilizations Study Group'?", "text", "1735478000", group_id, "17025551001", "wamid.event_001"],
    [20, "Temporal / Sequence", "Who sent a message shortly after the group title was updated in the second session?", "text", "Emma Thompson", group_id, "17025551003", "wamid.event_005"],
    
    # 5. Aggregation
    [21, "Aggregation", "How many unique documents were shared across both chat transcripts?", "number", "8", group_id, "", ""],
    [22, "Aggregation", "How many times was the 😂 reaction used?", "number", "3", group_id, "", ""],
    [23, "Aggregation", "How many total members are in the participants list?", "number", "5", group_id, "", ""],
    [24, "Aggregation", "Count the number of times Emma Thompson sent a message in the entire dataset.", "number", "28", group_id, "17025551003", ""],
    [25, "Aggregation", "How many images were shared in total?", "number", "8", group_id, "", ""],

    # 6. Comparison
    [26, "Comparison", "Who sent more messages: Emma Thompson or Michael Rodriguez?", "text", "Emma Thompson", group_id, "17025551003;17025551004", ""],
    [27, "Comparison", "Between David Chen and Sarah Martinez, who shared more documents?", "text", "David Chen", group_id, "17025551002;17025551001", ""],
    [28, "Comparison", "Which participant was the most active in the 'Ancient Egypt' topic discussions?", "text", "Emma Thompson", group_id, "17025551003", ""],
    [29, "Comparison", "Who sent the longest text message in the initial transcript?", "text", "Sarah Martinez", group_id, "17025551001", "wamid.event_004"],
    [30, "Comparison", "Who used more diverse emojis in their reactions: Michael or David?", "text", "Michael Rodriguez", group_id, "17025551004", ""],

    # 7. Null / False-Premise
    [31, "Null / False-Premise", "Why did John Smith leave the group?", "text", "John Smith is not a member of this group and there is no record of him leaving.", group_id, "", ""],
    [32, "Null / False-Premise", "What was the reason for the group being deleted?", "text", "The group was never deleted.", group_id, "", ""],
    [33, "Null / False-Premise", "List the details of the message where Sarah mentioned the 'Industrial Revolution'.", "text", "The Industrial Revolution was never mentioned; the focus was on Ancient Civilizations.", group_id, "", ""],
    [34, "Null / False-Premise", "Which user sent an Excel spreadsheet to the group?", "text", "No Excel spreadsheet was shared; only PDFs and images.", group_id, "", ""],
    [35, "Null / False-Premise", "When did the group change its name to 'Modern History'?", "text", "The group name was never changed to 'Modern History'.", group_id, "", ""],

    # 8. Relationship / Social Graph
    [36, "Relationship / Social Graph", "Who are the common members participating in discussions about both the Roman Empire and Ancient Egypt?", "list", "Sarah Martinez, David Chen, Emma Thompson, Michael Rodriguez, Lisa Anderson", group_id, "", ""],
    [37, "Relationship / Social Graph", "Which contact has the most incoming replies directed at them?", "text", "Sarah Martinez", group_id, "17025551001", ""],
    [38, "Relationship / Social Graph", "Identify the user who acted as the primary moderator or group starter.", "text", "Sarah Martinez", group_id, "17025551001", "wamid.event_001"],
    [39, "Relationship / Social Graph", "Who reacted to Lisa Anderson's messages the most?", "text", "Emma Thompson", group_id, "17025551003", ""],
    [40, "Relationship / Social Graph", "Is there any direct interaction between Lisa Anderson and Michael Rodriguez?", "text", "Yes, Lisa replied to Michael's video about pyramid construction.", group_id, "17025551005;17025551004", "wamid.event_020"],

    # 9. Conditional and Collection-Based
    [41, "Conditional and Collection-Based", "List all message IDs where Emma Thompson used an emoji reaction.", "list", "wamid.event_011; wamid.event_021; wamid.event_031", group_id, "17025551003", ""], # Sample placeholders
    [42, "Conditional and Collection-Based", "Provide a list of all filenames shared in the month of January 2025.", "list", "research_5.pdf, research_12.pdf, etc.", group_id, "", ""],
    [43, "Conditional and Collection-Based", "Which users shared an image and also sent a text message?", "list", "Michael Rodriguez, Sarah Martinez", group_id, "", ""],
    [44, "Conditional and Collection-Based", "List the unique topics discussed in the second transcript session.", "list", "Roman Empire, Ancient Egypt, Greeks, Maya Civilization, Mesopotamia", group_id, "", ""],
    [45, "Conditional and Collection-Based", "Identify all messages that received a '❤️' reaction.", "list", "wamid.event_032, wamid.event_055", group_id, "", ""],

    # 10. Evidence-Based
    [46, "Evidence-Based Interpretation", "What evidence is there that the group is interested in military history?", "text", "David Chen shared 'byzantine_military_tactics.pdf' and discussed 'divide and conquer' tactics.", group_id, "17025551002", "wamid.event_026;wamid.event_005"],
    [47, "Evidence-Based Interpretation", "How do we know the group title was updated to reflect a specific topic in the second session?", "text", "A system message indicated the title changed to 'Study Group - [Topic]'.", group_id, "", ""],
    [48, "Evidence-Based Interpretation", "Why did Emma Thompson find the Roman road networks impressive?", "text", "Because they built over 250,000 miles of roads, which she called 'incredible engineering'.", group_id, "17025551003", "wamid.event_006"],
    [49, "Evidence-Based Interpretation", "What indicates that Michael Rodriguez values the input of other members?", "text", "He stated he added 10 books to his reading list and thanked everyone for sharing their expertise.", group_id, "17025551004", "wamid.event_064"],
    [50, "Knowledge Graph Native Operations", "Are there any users who joined the group but never sent a message in the first session?", "text", "No, all users who joined (Sarah, David, Emma, Michael, Lisa) sent at least one message.", group_id, "", ""]
]

df_qa = pd.DataFrame(qa_data, columns=["question_id", "category", "question", "answer_type", "ground_truth_answer", "group_id", "user_ids", "message_ids"])
df_qa.to_csv('qa_dataset_extended.csv', index=False)
print("Saved 50 questions to qa_dataset_extended.csv")