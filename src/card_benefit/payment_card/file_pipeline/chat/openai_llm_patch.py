"""OpenAI adapter for the chatbot llm module. apply() is opt-in; no calls at import."""
from __future__ import annotations
import argparse, os
MODEL='gpt-6-luna'
_ORIGINALS=None

def apply(model=None, client=None):
    global _ORIGINALS
    import llm
    selected=model or MODEL
    if client is None:
        key=os.environ.get('OPENAI_API_KEY')
        if not key: raise RuntimeError('OPENAI_API_KEY environment variable is required')
        from openai import OpenAI
        client=OpenAI(api_key=key)
    if _ORIGINALS is None: _ORIGINALS=(llm.complete,llm.stream)
    def complete(system,user,max_tokens=400):
        result=client.chat.completions.create(model=selected,max_completion_tokens=max_tokens,messages=[{'role':'system','content':system},{'role':'user','content':user}])
        return result.choices[0].message.content or ''
    def stream(system,messages,max_tokens=800):
        result=client.chat.completions.create(model=selected,max_completion_tokens=max_tokens,messages=[{'role':'system','content':system},*messages],stream=True)
        for event in result:
            delta=event.choices[0].delta.content
            if delta: yield delta
    llm.complete=complete; llm.stream=stream
    return llm

def estimate(questions=60,input_tokens=1200,output_tokens=400):
    calls=questions*2; inp=calls*input_tokens; out=calls*output_tokens
    return {'label':'estimate','questions':questions,'calls':calls,'input_tokens':inp,'output_tokens':out,'estimated_cost_usd':inp*0.10/1_000_000+out*0.50/1_000_000}

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--estimate',action='store_true'); p.add_argument('--questions',type=int,default=60); p.add_argument('--input-tokens-per-call',type=int,default=1200); p.add_argument('--output-tokens-per-call',type=int,default=400); a=p.parse_args(argv)
    if not a.estimate: p.error('use --estimate; apply() is called by the harness')
    import json; print(json.dumps(estimate(a.questions,a.input_tokens_per_call,a.output_tokens_per_call)))
if __name__=='__main__': main()
