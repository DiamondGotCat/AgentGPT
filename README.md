# AgentGPT
GPT can Execute Your Custom Functions.

## Infomation

**Language:** Python

**License:** MIT License

**API:** OpenAI API (GPT)

## How

I simply taught GPT how to use the Function.

I used a notation that is easy for GPT to understand.

### Example
```
!AgentCode start
!runPython
!!runPython:script
result1 = len("Hello, World!")
!!
!!runPython:resultVar
result1
!!
!AgentCode end
```
