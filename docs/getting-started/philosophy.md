# Agents?

With all the hype in the industry I think it is important to define the overloaded term "agent". An AI agent is simply utilizing generative AI to complete a task. That task can be anything.

- **Chatbot**: Have a conversation with the user
- **Copilot**: Help the user write code
- **Custom**: Every time a Salesforce record is created write me an email describing it

As you can see, most of the use cases for agents have not strayed too far from the ability of an LLM to choose an appropriate tool or write some text. At least not yet. That is where Reagent comes in. We believe that with the proper utilization and checks LLM's can greatly surpass the trivial tasks they are used for nowadays.

# Philosophy

Reagent was built with 4 core principles in mind when it comes to the construction of agents.

- **Informed Decision**: Agents should be given as much information as possible to make decisions
- **Fast Feedback**: Agents should receive validation of actions taken as quickly as possible
- **Monotonic Decomposition**: Agents should always be able to make progress on a task by decomposing it into smaller tasks
- **Don't Know**: Agents should be able to say they don't know when they don't have the information or tools to complete a task