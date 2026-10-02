"""Labelled messages sent to a school office. POOL = examples the agent may show the model, TEST = new messages to route.

The school has some house rules that a stranger could not guess from the label names alone, for example:
  lunch money and meal accounts go to Cafeteria (not Office);   food-allergy forms go to Health (not Cafeteria);
  bike racks and parking go to Transport;   trip permission slips go to Activities;   late-arrival notes go to Office;
  the bus for a SCHOOL TRIP goes to Activities (not Transport);   lost clothes and school photos go to Office;
  sports injuries and medical certificates for sport go to Health (not Activities).
The examples are the only place where these rules are written down.
"""
LABELS = ["Office", "Cafeteria", "Transport", "Health", "Activities"]

POOL = [
    # Office: paperwork, certificates, notes about absence
    ("I need a certificate that Mia is a student here, for the bank.", "Office"),
    ("We moved house. How do I change our address on file?", "Office"),
    ("My son was late today because of the dentist, where do I hand in the note?", "Office"),
    ("Can I get a copy of last year's report card?", "Office"),
    ("My daughter lost her student ID card, how do we get a new one?", "Office"),
    ("How do I enrol my younger brother for next autumn?", "Office"),
    # Cafeteria: meals and lunch money
    ("How do I put money on my lunch account?", "Cafeteria"),
    ("What is on the menu on Thursday?", "Cafeteria"),
    ("Can my child get a vegetarian lunch every day?", "Cafeteria"),
    ("My lunch account is empty, will he still get a meal today?", "Cafeteria"),
    ("Is there a discount on lunches for families with three children?", "Cafeteria"),
    ("Where can I see how much my daughter spent in the canteen this month?", "Cafeteria"),
    # Transport: buses, bikes, parking
    ("What time does bus 12 leave from the school in the afternoon?", "Transport"),
    ("Is there a covered place to leave my bike at school?", "Transport"),
    ("Where can parents park when they pick up children?", "Transport"),
    ("How do I get a bus pass for my daughter?", "Transport"),
    ("The school bus did not come this morning, who do I call?", "Transport"),
    ("Can my son ride his scooter to school?", "Transport"),
    # Health: nurse, illness, allergies, medicine
    ("My son has a peanut allergy, which form do I fill in so the school knows?", "Health"),
    ("Can the nurse give my daughter her asthma medicine at noon?", "Health"),
    ("He fell in the playground and hurt his wrist, should we see a doctor?", "Health"),
    ("How many days must a child stay home after the flu?", "Health"),
    ("When is the vaccination day for the eighth grade?", "Health"),
    ("My child is gluten intolerant, who should I tell?", "Health"),
    # Activities: clubs, sports, music, trips
    ("How do I sign up for the chess club?", "Activities"),
    ("Where do I sign the permission slip for the museum trip?", "Activities"),
    ("When is football practice for the under-12 team?", "Activities"),
    ("Can my daughter join the school choir halfway through the term?", "Activities"),
    ("How much does the ski week cost, and can we pay in parts?", "Activities"),
    ("Is there a drama group for beginners?", "Activities"),
    # house rules that cross over
    ("What time does the bus leave for the trip to the zoo, and where do we meet?", "Activities"),
    ("Do we need to pay for the coach to the swimming gala?", "Activities"),
    ("My daughter left her jacket in the gym. Who keeps lost clothes?", "Office"),
    ("When are the class photos taken, and how do I order them?", "Office"),
    ("My son twisted his ankle in football, does he need a doctor's note before he can play again?", "Health"),
    ("Who signs the medical certificate so she can take part in the sports day?", "Health"),
]

# New messages, written differently from the pool. Several sit right on a house rule.
TEST = [
    ("How can I top up my kid's meal card online?", "Cafeteria"),
    ("My daughter is allergic to eggs. Do I need to tell the canteen or the nurse?", "Health"),
    ("Where can the students lock their bicycles?", "Transport"),
    ("Do I need to sign anything for the class trip to the science centre?", "Activities"),
    ("She arrived at 9:30 because of a doctor visit. Who gets the note?", "Office"),
    ("What is for lunch on Friday?", "Cafeteria"),
    ("The morning bus was 20 minutes late again.", "Transport"),
    ("My son has a fever, when can he come back?", "Health"),
    ("Is there a robotics club I can sign my daughter up for?", "Activities"),
    ("I need a letter confirming that my child attends this school.", "Office"),
    ("There is not enough money on his lunch card. What happens?", "Cafeteria"),
    ("Does the nurse keep an inhaler for my child at school?", "Health"),
    ("Can parents drop children off right at the gate by car?", "Transport"),
    ("What does the summer sports camp cost?", "Activities"),
    ("We changed phone number and email, where do I update them?", "Office"),
    ("My son is vegan. Can the canteen cook for him?", "Cafeteria"),
    ("When does the coach to the museum pick the children up?", "Activities"),
    ("Where do I find my son's lost scarf?", "Office"),
    ("Can I order the school photo of my twins as a set?", "Office"),
    ("Our daughter sprained her knee in gym class. Can she skip swimming this week?", "Health"),
    ("Is the bus for the camping weekend free?", "Activities"),
    ("A doctor's note for sports day, who needs to see it?", "Health"),
    ("Which stop does the number 7 bus use near the school?", "Transport"),
    ("She dropped her lunch card on the way. Can it be blocked?", "Cafeteria"),
]
