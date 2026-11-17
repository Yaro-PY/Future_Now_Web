import test from 'node:test';
import assert from 'node:assert/strict';
import {readRoute,readOpportunityId,authReturnPath,internalClick} from '../frontend/src/routing/routes.js';
test('listing URLs coexist with account hash routes',()=>{
  globalThis.location={pathname:'/opportunities/42/python',hash:'#saved',search:''};
  assert.equal(readRoute(),'opportunity');assert.equal(readOpportunityId(),42);
  location={pathname:'/',hash:'#saved',search:''};assert.equal(readRoute(),'saved');
  assert.equal(readOpportunityId('/opportunities/abc'),null);
  assert.equal(readOpportunityId('/opportunities/999999999999999999999'),null);
});
test('sign-in return rejects external and private targets',()=>{
  for(const next of ['https://evil.example/','//evil.example/','/settings','/opportunities/1/x?next=evil','/opportunities/1/x#fragment','/opportunities/1/\\evil']){
    globalThis.location={search:'?next='+encodeURIComponent(next)};assert.equal(authReturnPath(),null);
  }
  location.search='?next='+encodeURIComponent('/opportunities/42/python');assert.equal(authReturnPath(),'/opportunities/42/python');
});
test('modified and middle clicks retain native link behavior',()=>{
  const click={button:0,metaKey:false,ctrlKey:false,shiftKey:false,altKey:false};
  assert(internalClick(click));
  for(const change of [{button:1},{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true}])assert(!internalClick({...click,...change}));
});
