# REAGENT

Welcome 👋

[Docs](https://docs.hokyo.ai/reagent/getting-started/installation/)

Reagent is a free and open source library for building AI Agents. AI Agents use generative AI to complete tasks rather than just generate text. Reagent is built for agents to complete complex long-lived tasks without error. Read more about our [agent philosophy](https://docs.hokyo.ai/reagent/getting-started/philosophy/).

Reagent was built with 3 goals in mind.
1. Build agents that can actually complete complicated tasks.
2. Make it as easy as possible to do so.
3. Production ready deployment.

To get started with the library check out the [quick start](https://docs.hokyo.ai/reagent/getting-started/quick-start/) tutorial at our documentation page.

If you would like to contribute you are in the right place.
Morphing:
Dry run the task with no defined action space, let the agent be creative in the tools and delegates it would want to use
Then display the existing tools and delegates and create a list of updates/additions
With the new action space let the agent try again and assess
If the agent fails, add that info to the agent memories and allow

Learning:
Complete the task hydrated with information, let the agent make fully informed decisions
If the agent fails, update the information it had access to and let it try again

Morphing should only be used in development
Production agents should not morph, but can learn
Using an morphing agent in parallel might to inconsistent states because the action space will change
Auto morphing can be used to allow agents to morph when they detect a need


To run Hatchet tests:
docker compose -f ./docker/compose.hatchet-lite.yaml up
cat <<EOF >> .env
HATCHET_CLIENT_TOKEN="$(docker compose -f ./docker/compose.hatchet-lite.yaml exec hatchet-lite /hatchet-admin token create --config /config --tenant-id 707d0855-80ab-4e1f-a156-f1c4546cbf52 | xargs)"
HATCHET_CLIENT_TLS_STRATEGY=none
EOF
