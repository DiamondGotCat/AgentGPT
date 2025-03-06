import json
import subprocess
from openai import OpenAI

# ---------- OpenAI API Init ---------- #

client = OpenAI()

# ---------- Simple Variables ---------- #

localVars = {}
chatHistory = []

# ---------- Simple Functions ---------- #

def convertCommandsToText(available_commands):
    serializable_commands = []
    for cmd in available_commands:
        serializable_commands.append({
            "id": cmd["id"],
            "args": cmd["args"],
            "desc": cmd["desc"].strip()
        })
    return json.dumps(serializable_commands, indent=2, ensure_ascii=False)

# ---------- OpenAI API Functions ---------- #

def getOneResponse(chat_history, model_id):
    response = client.chat.completions.create(model=model_id,
    messages=chat_history)
    return response.choices[0].message.content

# ---------- AgentCode Commands ---------- #

def runPython(script, resultVar):
    exec(script, globals(), localVars)
    result = localVars.get(resultVar)
    globals().update(localVars)
    return result

def runShellCommand(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

# ---------- Parser ---------- #

def parse_agent_code(response):
    lines = response.splitlines()
    in_block = False
    commands = []
    current_command = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "!AgentCode start":
            in_block = True
            i += 1
            continue
        if line == "!AgentCode end":
            in_block = False
            i += 1
            continue
        if in_block:
            if line.startswith("!") and not line.startswith("!!"):
                if current_command:
                    commands.append(current_command)
                command_id = line[1:].strip()
                current_command = {"id": command_id, "args": {}}
                i += 1
                continue
            elif line.startswith("!!"):
                if current_command is None:
                    i += 1
                    continue
                header = line[2:]
                if ":" not in header:
                    i += 1
                    continue
                header_parts = header.split(":", 1)
                cmd_id = header_parts[0].strip()
                arg_name = header_parts[1].strip()
                arg_lines = []
                i += 1
                while i < len(lines) and lines[i].strip() != "!!":
                    arg_lines.append(lines[i])
                    i += 1
                i += 1
                arg_value = "\n".join(arg_lines).strip()
                current_command["args"][arg_name] = arg_value
                continue
            else:
                i += 1
                continue
        else:
            i += 1
    if current_command:
        commands.append(current_command)
    return commands

# ---------- Main Functions ---------- #

def getResponse(chat_history, model_id, available_commands):
    chat_history_local = [
        {
            "role": "system",
            "content": f"""
You are an excellent assistant.  
You can use AgentCode to access various functionalities.  

Using AgentCode is simple.  
All you have to do is say something like the following in your response:

---
!AgentCode start  
!runPython  
!!runPython:script  
result1 = len("Hello, World!")  
!!  
!!runPython:resultVar  
result1  
!!  
!AgentCode end  
---

After saying this, you should end your response.  
Once your response ends, the system (role) will report the result back to you.  

Below is a list of available AgentCode commands:

```
{convertCommandsToText(available_commands)}
```
"""
        }
    ] + chat_history

    responseFromGPT = getOneResponse(chat_history_local, model_id)
    chatHistory.append({"role": "assistant", "content": responseFromGPT})

    commands = parse_agent_code(responseFromGPT)
    available_commands_by_id = {cmd["id"]: cmd for cmd in available_commands}

    if 0 < len(commands):

        for command in commands:
            cmd_id = command["id"]
            if cmd_id in available_commands_by_id:
                action_func = available_commands_by_id[cmd_id]["action"]
                try:
                    result = action_func(**command["args"])
                    chatHistory.append({"role": "system", "content": f"'{cmd_id}'の実行が完了しました。\nresult: {result}"})
                    print(f"(AgentCode) {cmd_id} has Executed.\n    Args: {command['args']}\n   Result: {result}")

                except Exception as e:
                    chatHistory.append({"role": "system", "content": f"'{cmd_id}'の実行中にエラーが発生しました。\nエラー: {e}"})
            else:
                chatHistory.append({"role": "system", "content": f"未知のコマンド: '{cmd_id}'"})
        
        getResponse(chatHistory, model_id, available_commands)

    else:
        print(responseFromGPT)

    return responseFromGPT

# ---------- Main Variables ---------- #

availableCommands = [
    {
        "id": "runPython",
        "args": [
            "script",
            "resultVar"
        ],
        "desc": """
Execute Python Script.
You should save the result in a variable of your choice within your script.

Arguments:
- script: Python Script
- resultVar: Variable Name of Saved Result Data

Output:
- result: Content of resultVar
""",
        "action": runPython
    },
    {
        "id": "runShellCommand",
        "args": [
            "command"
        ],
        "desc": """
Execute a shell command.
This command will run the provided shell command and return its standard output.

Arguments:
- command: The shell command to execute as a string.

Output:
- result: Standard output of the shell command execution.
""",
        "action": runShellCommand
    },
    {
        "id": "endChat",
        "args": [],
        "desc": """
End this Chat.
""",
        "action": exit
    }
]

# ---------- Main ---------- #

if __name__ == "__main__":
    while True:
        prompt = input(">>> ")
        chatHistory.append({"role": "user", "content": prompt})
        response = getResponse(chatHistory, "gpt-4o-mini", availableCommands)
