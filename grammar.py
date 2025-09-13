import re

class Grammar:
    def __init__(self):
        # Basic parts of speech patterns
        self.nouns = set()
        self.verbs = set()
        self.adjectives = set()
        self.adverbs = set()
        self.prepositions = set()
        self.conjunctions = set()
        self.pronouns = set()
        self.articles = set(['a', 'an', 'the'])

    def add_words(self, word_list, pos):
        if pos == 'noun':
            self.nouns.update(word_list)
        elif pos == 'verb':
            self.verbs.update(word_list)
        elif pos == 'adjective':
            self.adjectives.update(word_list)
        elif pos == 'adverb':
            self.adverbs.update(word_list)
        elif pos == 'preposition':
            self.prepositions.update(word_list)
        elif pos == 'conjunction':
            self.conjunctions.update(word_list)
        elif pos == 'pronoun':
            self.pronouns.update(word_list)
        elif pos == 'article':
            self.articles.update(word_list)

    def tokenize(self, sentence):
        # Simple tokenizer splitting on spaces and punctuation
        tokens = re.findall(r"\\b\\w+\\b", sentence.lower())
        return tokens

    def identify_pos(self, word):
        # Identify part of speech for a word based on known sets
        if word in self.nouns:
            return 'noun'
        elif word in self.verbs:
            return 'verb'
        elif word in self.adjectives:
            return 'adjective'
        elif word in self.adverbs:
            return 'adverb'
        elif word in self.prepositions:
            return 'preposition'
        elif word in self.conjunctions:
            return 'conjunction'
        elif word in self.pronouns:
            return 'pronoun'
        elif word in self.articles:
            return 'article'
        else:
            return 'unknown'

    def parse_sentence(self, sentence):
        # Parse sentence into parts of speech sequence
        tokens = self.tokenize(sentence)
        pos_sequence = [(token, self.identify_pos(token)) for token in tokens]
        return pos_sequence

    def is_valid_sentence(self, sentence):
        # Basic validation: sentence must have at least one noun and one verb
        pos_seq = self.parse_sentence(sentence)
        has_noun = any(pos == 'noun' for _, pos in pos_seq)
        has_verb = any(pos == 'verb' for _, pos in pos_seq)
        return has_noun and has_verb

    def generate_sentence(self, words):
        # Generate a simple sentence from given words using basic grammar rules
        # This is a naive implementation for demonstration
        nouns = [w for w in words if self.identify_pos(w) == 'noun']
        verbs = [w for w in words if self.identify_pos(w) == 'verb']
        adjectives = [w for w in words if self.identify_pos(w) == 'adjective']

        if not nouns or not verbs:
            return "I don't have enough information to form a sentence."

        subject = nouns[0]
        verb = verbs[0]
        adjective = adjectives[0] if adjectives else ''

        sentence = f"The {adjective} {subject} {verb}s." if adjective else f"The {subject} {verb}s."
        return sentence
