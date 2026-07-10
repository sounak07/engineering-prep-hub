f"""

Machine Coding
AI Task Orchestration Engine
Background
You are building an internal AI Orchestration Engine for Observe.AI.
The platform executes AI-powered workflows like:
Call Summarization
AI Evaluator
AI Coaching
Sentiment Analysis
Agentic Insights
Each workflow consists of multiple independent AI tasks.
Example workflow:
Workflow: Coaching

Tasks:
- Summarize transcript
- Extract Action Items
- Evaluate using Knowledge Base
- Compute QA Score
- Generate Coaching Feedback


Each task can be executed by multiple LLM providers.
Available providers:
GPT-5
Claude
Gemini
Llama
Grok

Each provider has different:
cost
token limit
latency
availability

A provider may randomly:
fail
timeout
become unavailable
The execution itself can be mocked using:
Thread.sleep(...)
Random success/failure
No external API calls are required.

Constraints
Everything should be in-memory.
No database.
No frameworks required.
Focus on clean object-oriented design.
The design should be extensible for adding new providers or routing strategies.


Phase 1 (Mandatory)
Implement an asynchronous task execution engine.
Requirements:

Client submits a workflow.
Workflow contains multiple independent tasks.

Tasks should execute in parallel.
The workflow should complete only after all tasks finish.
Print task status.

Example:
Workflow Started

Task-1 -> Running
Task-2 -> Running
Task-3 -> Running

Task-2 -> Completed
Task-1 -> Completed
Task-3 -> Failed

Workflow Completed


LLMProvider:
    @cost()

    @token_limit()

    @is_available()

    @evaluate_inputs



Task:
    execute(llm_config)

    check_status()


SummariseTranscript(Task):
    // instructions: str, meta_data: dict


    def execute(llm_config: LLMProvider):
        // build_data
        // call the LLM
        // return the result


OrchestrationService:
    task: list[Task]

    def evaluate()
        // create tasks
        // use semaphore
        // compile the results
        // return them 

"""


from abc import ABC, abstractmethod
import asyncio
from enum import Enum
import random
import time


class TaskStatus(Enum):
    COMPLETED = "1"
    PENDING = "2"
    FAILED = "3"



class LLMProvider(ABC):
    @abstractmethod
    def llm_cost(self) -> int:
        ...

    @abstractmethod
    def get_llm_token_limit(self) -> int:
        ...

    @abstractmethod
    def is_llm_available(self) -> bool:
        ...

    @abstractmethod
    def evaluate_inputs(self, task_data: dict):
        ...

class Task(ABC):
    def __init__(self) -> None:
        self.task: TaskStatus = TaskStatus.PENDING

    @abstractmethod
    def execute(self, llm_provider: LLMProvider) -> dict:
        ...

    @abstractmethod
    def update_task_status(self, updated_status: TaskStatus):
        self.task = updated_status

    @abstractmethod
    def status(self) -> TaskStatus:
        ...

    

class SummariseTranscript(Task):
    def __init__(self, task_name: str, meta_data: dict) -> None:
        super().__init__()
        self.task_name = task_name
        self.meta_data = meta_data

    def update_task_status(self, updated_status: TaskStatus) -> None:
        self.task = updated_status

    def status(self) -> TaskStatus:
        return self.task

    def execute(self, llm_provider: LLMProvider) -> dict:
        print(f"{self.task_name} -> Running")
        input_data = {
            "name": self.task_name,
            "data": self.meta_data,
        }

        try:
            res = llm_provider.evaluate_inputs(task_data=input_data)
            self.update_task_status(TaskStatus.COMPLETED)
            print(f"{self.task_name} -> Completed")
            return {"task": self.task_name, "status": self.status(), "result": res}
        except Exception as e:
            self.update_task_status(TaskStatus.FAILED)
            print(f"{self.task_name} -> Failed")
            return {"task": self.task_name, "status": self.status(), "error": str(e)}


def mock_ll_call():
    number = random.randint(1, 100)

    if number%2 == 0:
        time.sleep(random.uniform(5,6))  # random delay midway
        number = random.randint(1, 100)
        print("Suscess")
        return
    else:
        raise Exception("Call failed")

class GPT(LLMProvider):
    def __init__(self, cost_per_mil_token: int, token_limit: int) -> None:
        self.cost_per_mil_token = cost_per_mil_token
        self.token_limit = token_limit

    
    def get_llm_token_limit(self) -> int:
        return self.token_limit

    def llm_cost(self) -> int:
        return self.cost_per_mil_token

    def is_llm_available(self) -> bool:
        return True

    def evaluate_inputs(self, task_data: dict):
        time.sleep(random.uniform(5,6))
        print(f"Current == {task_data}")
        try:
            mock_ll_call()
        except Exception:
            raise


MAX_CONCURRENT = 5

class OrchestrationService:
    # OrchestrationService:
    # task: list[Task]

    # def evaluate()
    #     // create tasks
    #     // use semaphore
    #     // compile the results
    #     // return them 
    def __init__(self, tasks: list[Task], llm_provider: LLMProvider) -> None:
        self._tasks: list[Task] = tasks
        self._llm_provider: LLMProvider = llm_provider
        self._semaphore = asyncio.Semaphore(5)

    @property
    def pick_llm_provider(self, provider: LLMProvider) -> bool:
        if self._llm_provider.is_llm_available():
            return self._llm_provider
        raise Exception("LLM not available")

    async def run_with_semaphore(self, tasks: list[Task]):

        async def worker(task: Task):
            async with self._semaphore:
                return asyncio.to_thread(task.execute, self.pick_llm_provider)

        task_handles = [asyncio.create_task(worker(task)) for task in tasks]
        return asyncio.gather(*task_handles)

    async def execute_all(self):
        return asyncio.run(self.run_with_semaphore(self._tasks))



def _demo():
    print("Workflow Started\n")

    gpt = GPT(cost_per_mil_token=10, token_limit=8192)
    tasks = [
        SummariseTranscript("Task-1", {"transcript": "Agent handled billing inquiry."}),
        SummariseTranscript("Task-2", {"transcript": "Customer requested a callback."}),
        SummariseTranscript("Task-3", {"transcript": "Escalation due to repeated issue."}),
    ]

    service = OrchestrationService(tasks=tasks, llm_provider=gpt)
    results = service.execute_all()

    print("\nWorkflow Completed")
    return results


if __name__ == "__main__":
    _demo()

