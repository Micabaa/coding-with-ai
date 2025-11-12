# Contents of /AI_Karaoke_Project/judge_agent/judge_server.py

class JudgeServer:
    def __init__(self):
        self.judging_criteria = self.load_judging_criteria()

    def load_judging_criteria(self):
        # Load criteria from personality prompts
        criteria = {
            "strict": self.load_personality_prompts("strict_judge.txt"),
            "supportive": self.load_personality_prompts("supportive_grandma.txt")
        }
        return criteria

    def load_personality_prompts(self, filename):
        with open(f'personality_prompts/{filename}', 'r') as file:
            return file.readlines()

    def evaluate_performance(self, performance_data):
        # Evaluate the performance based on criteria
        # This is a placeholder for evaluation logic
        evaluation_results = {}
        for personality, prompts in self.judging_criteria.items():
            evaluation_results[personality] = self.perform_evaluation(performance_data, prompts)
        return evaluation_results

    def perform_evaluation(self, performance_data, prompts):
        # Placeholder for actual evaluation logic
        return f"Evaluated performance with prompts: {''.join(prompts)}"

    def start(self):
        # Start the judge server
        print("Judge Server is running...")

if __name__ == "__main__":
    server = JudgeServer()
    server.start()