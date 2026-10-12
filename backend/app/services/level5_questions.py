"""Reviewed Level 5 quiz questions: 25 distinct items."""

LEVEL_5_QUESTIONS = [
  {
    "id": "advanced-l5-01",
    "question": "What does expected goals (xG) primarily estimate?",
    "options": [
      "The likelihood that a given shot becomes a goal",
      "The number of goals a team is guaranteed to score",
      "The probability of winning the league",
      "The total number of passes before a goal"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-02",
    "question": "What does expected assists (xA) typically measure?",
    "options": [
      "The expected-goal value of shots created by a player's passes",
      "The number of assists guaranteed next match",
      "The value of all defensive clearances",
      "The total distance covered by a midfielder"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-03",
    "question": "Why can a team's xG exceed its actual goals in one match?",
    "options": [
      "Shot chances had higher estimated scoring likelihood than the goals scored",
      "The referee removed a scored goal from xG",
      "Every missed shot counts as a goal",
      "The team necessarily committed more fouls"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-04",
    "question": "What is a key limitation of single-match xG?",
    "options": [
      "It describes chance quality probabilistically, not a guaranteed result",
      "It counts only penalties",
      "It ignores all shot locations",
      "It can only be used after extra time"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-05",
    "question": "What does PPDA commonly represent in football analysis?",
    "options": [
      "Opposition passes allowed per defensive action in selected zones",
      "Points per domestic appearance",
      "Penalties per defensive attacker",
      "Passes played during added time"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-06",
    "question": "What can a low PPDA value often suggest?",
    "options": [
      "A team is applying relatively frequent defensive pressure",
      "A team always keeps a clean sheet",
      "A team cannot counterattack",
      "A team has no midfielders"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-07",
    "question": "What is field tilt in football analytics?",
    "options": [
      "A measure of territorial possession based on final-third activity",
      "The physical slope of the pitch",
      "The average shot height",
      "The proportion of headers won"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-08",
    "question": "What is progressive passing?",
    "options": [
      "Passing that meaningfully advances the ball toward the opponent's goal",
      "Passing only to the goalkeeper",
      "Passing across the halfway line exactly once",
      "Passing only after substitutions"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-09",
    "question": "Why is possession percentage alone insufficient to assess attacking quality?",
    "options": [
      "It does not directly show the danger of chances created",
      "It always excludes goalkeeper passes",
      "It measures only shots on target",
      "It is calculated only at halftime"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-10",
    "question": "What does a shot map typically display?",
    "options": [
      "Locations from which attempts were taken",
      "The running speed of every player",
      "The exact offside line at every moment",
      "The referee's positioning throughout the match"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-11",
    "question": "What is a pass network?",
    "options": [
      "A visualization of passing connections and patterns among teammates",
      "A rule limiting pass direction",
      "A diagram of all referees",
      "A ranking of stadium attendance"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-12",
    "question": "What is an expected-threat (xT) model designed to value?",
    "options": [
      "How actions move the ball into positions associated with future scoring danger",
      "The probability of a red card",
      "The number of fans attending a match",
      "The length of injury time"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-13",
    "question": "Why might an analyst compare per-90-minute statistics?",
    "options": [
      "To account for differences in playing time",
      "To guarantee identical opponent quality",
      "To remove all effects of tactics",
      "To exclude substitute appearances"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-14",
    "question": "What is selection bias in player comparisons?",
    "options": [
      "Misleading conclusions when the compared samples differ systematically",
      "An error caused only by yellow cards",
      "A rule preventing player transfers",
      "A calculation that uses too many decimal places"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-15",
    "question": "Why should a model account for opponent strength?",
    "options": [
      "Strong and weak opposition can affect observed performances",
      "Opponent quality never changes results",
      "All matches have identical conditions",
      "It eliminates the need for data validation"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-16",
    "question": "What is overfitting in a match prediction model?",
    "options": [
      "Learning noise in training data that does not generalize well",
      "Predicting exactly one scoreline",
      "Using more than one data source",
      "Training only on home matches"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-17",
    "question": "What is data leakage in sports prediction?",
    "options": [
      "Using information unavailable at the time a prediction would be made",
      "Losing a spreadsheet during training",
      "Sharing a match result publicly",
      "Removing old fixtures from a dataset"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-18",
    "question": "What is a calibration plot used for?",
    "options": [
      "Checking whether predicted probabilities align with observed frequencies",
      "Displaying only player heights",
      "Ranking teams alphabetically",
      "Calculating stadium capacity"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-19",
    "question": "What does a 70% predicted win probability mean?",
    "options": [
      "Across similarly predicted matches, wins should occur about 70% of the time if calibrated",
      "The team will definitely win 7–0",
      "The team must win its next seven matches",
      "The opponent has no chance to win"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-20",
    "question": "Why are time-based validation splits useful for football prediction?",
    "options": [
      "They better mimic predicting future matches from past information",
      "They guarantee perfect accuracy",
      "They remove the need for test data",
      "They prevent teams from changing managers"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-21",
    "question": "What is the Brier score used to evaluate?",
    "options": [
      "Accuracy of probabilistic predictions against observed outcomes",
      "Total distance covered by defenders",
      "The number of passes per match",
      "The average ticket price"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-22",
    "question": "Why is a baseline model important in sports ML?",
    "options": [
      "It shows whether a complex model improves on a simple reference",
      "It guarantees the model is unbiased",
      "It removes all uncertainty",
      "It determines the match referee"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-23",
    "question": "What is home advantage as a modeling feature?",
    "options": [
      "A possible performance difference associated with playing at home",
      "A rule giving the home team an extra player",
      "A guaranteed goal for the hosts",
      "A statistic that never changes"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-24",
    "question": "What is concept drift in a football prediction system?",
    "options": [
      "A change over time in relationships between inputs and outcomes",
      "A change in the stadium's longitude",
      "A player's position during a throw-in",
      "A shift in kickoff time only"
    ],
    "answer": 0,
    "min_level": 5
  },
  {
    "id": "advanced-l5-25",
    "question": "Why should prediction models report uncertainty?",
    "options": [
      "Football outcomes are variable even with informative data",
      "All predictions are deterministic",
      "Probabilities always add to more than one",
      "Uncertainty guarantees a draw"
    ],
    "answer": 0,
    "min_level": 5
  }
]
