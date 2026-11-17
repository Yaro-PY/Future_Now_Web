import test from 'node:test';
import assert from 'node:assert/strict';
import {gandalfDestination} from '../frontend/src/effects/gandalfBehavior.js';
const base={time:10000,phase:1,width:1000,height:800,pointer:{x:500,y:400,at:-Infinity},target:{x:200,y:300}};
test('a guide keeps clear of the pointer and turns inward near the edge',()=>{
  let result=gandalfDestination({...base,pointer:{x:500,y:400,at:9500}});assert.equal(result.state,'guide');assert.equal(result.x,564);assert.equal(result.y,360);
  result=gandalfDestination({...base,pointer:{x:950,y:400,at:9500}});assert(result.x<950);
});
test('an idle guide rests briefly, then wanders; user interaction takes priority',()=>{
  assert.deepEqual(gandalfDestination({...base,time:20500}),{state:'rest',x:200,y:300});
  assert.equal(gandalfDestination({...base,time:22500}).state,'wander');
  assert.equal(gandalfDestination({...base,time:20500,pointer:{x:500,y:400,at:20000}}).state,'guide');
});
