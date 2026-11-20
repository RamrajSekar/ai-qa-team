const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const ts=require('typescript');
function harness(apiFetch){
 const states=[];let index=0,lastDeps,cleanup,effect,context;
 const react={createContext: value=>(context={value,Provider:'Provider'}),useContext:()=>context.value,
  useState: initial=>{const slot=index++;if(!(slot in states))states[slot]=initial;return [states[slot],next=>{states[slot]=typeof next==='function'?next(states[slot]):next;}];},
  useCallback:fn=>fn,useEffect:(fn,deps)=>{if(!lastDeps||deps.some((value,i)=>value!==lastDeps[i])){effect=fn;lastDeps=deps;}}};
 const exports={};const code=ts.transpileModule(fs.readFileSync('src/components/providers/FeatureFlagsProvider.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(code,{exports,AbortSignal,require:name=>name==='react'?react:name==='next/navigation'?{usePathname:()=>'/projects/P/stories'}:name==='@/utils/api'?{apiFetch}:require(name)});
 function render(){index=0;const tree=exports.FeatureFlagsProvider({children:null});context.value=tree.props.value;if(effect){cleanup?.();cleanup=effect();effect=null;}return exports.useFeatures();}
 return {render,settle:async()=>{await new Promise(resolve=>setImmediate(resolve));return render();},unmount:()=>cleanup?.()};
}
test('failed feature loading stays closed until explicit retry then recovers',async()=>{
 let calls=0;const fixture=harness(async()=>{calls++;if(calls===1)throw new Error('timeout');return {ok:true,data:{story_management:true}};});
 assert.equal(fixture.render().ready,false);
 const failed=await fixture.settle();assert.equal(failed.failed,true);assert.equal(failed.enabled('story_management'),false);
 fixture.render();assert.equal(calls,1);
 failed.retry();assert.equal(fixture.render().ready,false);
 const recovered=await fixture.settle();assert.equal(recovered.failed,false);assert.equal(recovered.enabled('story_management'),true);assert.equal(calls,2);
});
test('malformed settings never enable features',async()=>{
 const fixture=harness(async()=>({ok:true,data:{story_management:'true'}}));fixture.render();
 assert.equal((await fixture.settle()).failed,true);
});
test('unmounted request cannot update settings',async()=>{
 let resolve;const fixture=harness(()=>new Promise(done=>resolve=done));fixture.render();fixture.unmount();
 resolve({ok:true,data:{story_management:true}});
 assert.equal((await fixture.settle()).enabled('story_management'),false);
});
