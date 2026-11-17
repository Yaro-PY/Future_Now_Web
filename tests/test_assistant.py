"""Real API/SQLite assistant regressions; no network or external AI model."""
from datetime import timedelta
from tests.test_api import APITests,opportunity
import database as db

class AssistantTests(APITests):
    async def seed(self):
        await self.register()
        await db.upsert_events([
            opportunity(1,title='Python з нуля',min_age=12,max_age=17),
            opportunity(2,title='Advanced Python',min_age=18,max_age=100,is_free=False),
            opportunity(3,title='Python offline basics',format='offline',min_age=14,max_age=17),
            opportunity(4,title='English for beginners'),
            opportunity(5,title='Figma та графічний дизайн',min_age=18,max_age=100,topics=['art']),
            opportunity(6,title='Основи Web UI розробки',min_age=12,max_age=17,topics=['it']),
            opportunity(7,title='Expired Python',deadline=db.localnow()-timedelta(days=2)),
            opportunity(8,title='Python intro with unknown ages',min_age=None,max_age=None),
            opportunity(9,title='Linux basics',topics=['it']),
            opportunity(10,title='Python grant',event_type='grant'),
            opportunity(11,title='Python price unknown',price_known=False,is_free=False),
        ])

    async def ask(self,text,context=None):
        response=await self.request('POST','/assistant/message',json={'message':text,'context':context})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def test_auth_csrf_and_validation(self):
        self.assertEqual((await self.client.post('/api/v1/assistant/message',json={'message':'hi'})).status_code,401)
        await self.register()
        self.assertEqual((await self.client.post('/api/v1/assistant/message',json={'message':'hi'})).status_code,403)
        for body in ({'message':' '},{'message':'x'*1001},{'message':'hi','context':{'filters':{'age':'invalid'}}},
                     {'message':'hi','context':{'age_min':17,'age_max':12}},
                     {'message':'hi','context':{'terms':['x'*51]}}):
            response=await self.request('POST','/assistant/message',json=body)
            self.assertEqual(response.status_code,422,response.text)

    async def test_greetings_and_help_do_not_guess_courses(self):
        await self.register()
        for text,language in (('Привіт','uk'),('привет','ru'),('hello','en')):
            result=await self.ask(text)
            self.assertEqual(result['kind'],'greeting')
            self.assertEqual(result['context']['language'],language)
            self.assertEqual(result['results'],[])
        result=await self.ask('как найти курс')
        self.assertEqual(result['kind'],'clarify')
        result=await self.ask('как добавить курс')
        self.assertEqual(result['kind'],'help')
        self.assertEqual(result['actions'][0]['route'],'suggest')

    async def test_followups_keep_topic_format_price_and_exact_age(self):
        await self.seed()
        first=await self.ask('найди курсы программирования')
        self.assertEqual(first['context']['terms'],['programming'])
        second=await self.ask('а есть варианты только бесплатные онлайн?',first['context'])
        self.assertEqual(second['context']['terms'],['programming'])
        self.assertEqual(second['context']['filters']['format'],'online')
        self.assertEqual(second['context']['filters']['criteria'],['free'])
        result=await self.ask('мне 16',second['context'])
        self.assertEqual(result['context']['age_min'],16)
        self.assertEqual(result['context']['age_max'],16)
        self.assertEqual({item['title'] for item in result['results']},{'Python з нуля','Основи Web UI розробки'})
        self.assertEqual(result['total'],2)

    async def test_beginner_python_is_grounded_and_expired_unknown_prices_are_excluded(self):
        await self.seed()
        result=await self.ask('Найди бесплатный онлайн курс Python с нуля, мне 16')
        self.assertEqual([item['title'] for item in result['results']],['Python з нуля'])
        self.assertEqual(result['context']['level'],'beginner')
        self.assertTrue(result['results'][0]['price']['is_free'])

    async def test_topic_change_and_explicit_age_relaxation(self):
        await self.seed()
        result=await self.ask('Бесплатные онлайн курсы Python, мне 16')
        design=await self.ask('а по дизайну',result['context'])
        self.assertEqual(design['context']['terms'],['design'])
        self.assertEqual(design['total'],0)
        self.assertEqual(design['context']['age_min'],16)
        relaxed=await self.ask('любой возраст',design['context'])
        self.assertEqual([item['title'] for item in relaxed['results']],['Figma та графічний дизайн'])
        self.assertEqual(relaxed['context']['filters']['criteria'],['free'])

    async def test_unrecognized_topic_is_not_discarded_when_price_and_format_are_parsed(self):
        await self.seed()
        result=await self.ask('Найди бесплатные онлайн курсы по Linux')
        self.assertEqual(result['context']['terms'],['linux'])
        self.assertEqual([item['title'] for item in result['results']],['Linux basics'])

    async def test_more_results_and_no_automatic_relaxation(self):
        await self.seed()
        result=await self.ask('Покажи все курсы')
        self.assertTrue(result['has_more'])
        more=await self.ask(result['more_label'],result['context'])
        self.assertEqual(more['page'],2)
        self.assertFalse({item['id'] for item in more['results']}&{item['id'] for item in result['results']})
        missing=await self.ask('Найди бесплатный офлайн курс немецкого, мне 14')
        self.assertEqual(missing['results'],[])
        self.assertEqual(missing['context']['filters']['format'],'offline')
        self.assertEqual(missing['context']['age_min'],14)
        self.assertIn('Любой возраст',missing['suggestions'])

    async def test_assistant_does_not_change_saved_catalogue_filters(self):
        await self.seed()
        await self.request('PUT','/me/filters',json={'type':'contest','country':'europe'})
        before=(await self.client.get('/api/v1/me/filters')).json()
        await self.ask('Найди курсы английского онлайн')
        after=(await self.client.get('/api/v1/me/filters')).json()
        self.assertEqual(before,after)

    async def test_localized_labels_age_relaxation_and_last_page(self):
        await self.seed()
        first=await self.ask('Курсы программирования, мне уже 16, только онлайн')
        self.assertIn('Программирование',first['labels'])
        self.assertEqual(first['context']['age_min'],16)
        relaxed=await self.ask('без возрастных ограничений',first['context'])
        self.assertEqual(relaxed['context']['terms'],['programming'])
        self.assertIsNone(relaxed['context']['age_min'])
        current=relaxed
        while current['has_more']:
            current=await self.ask(current['more_label'],current['context'])
        self.assertGreater(current['page'],1)
        self.assertIn('последние курсы',current['message'])

    async def test_ukrainian_and_english_followups_keep_preferences(self):
        await self.seed()
        english=await self.ask('Find free online Python courses for beginners, I am 16')
        self.assertEqual(english['context']['language'],'en')
        self.assertEqual([item['title'] for item in english['results']],['Python з нуля'])
        ukrainian=await self.ask('Мені вже 16, безкоштовні курси Python онлайн для початківців')
        self.assertEqual(ukrainian['context']['language'],'uk')
        self.assertEqual([item['title'] for item in ukrainian['results']],['Python з нуля'])
        self.assertIn('Для початківців',ukrainian['labels'])

    async def test_gandalf_easter_eggs_preserve_the_course_search(self):
        await self.seed()
        first=await self.ask('Бесплатные курсы Python, мне 16')
        for phrase in ('Гэндальф','ты не пройдёшь','где кольцо'):
            result=await self.ask(phrase,first['context'])
            self.assertEqual(result['kind'],'wizard')
            self.assertEqual(result['results'],[])
            self.assertEqual(result['context'],first['context'])
            self.assertIn('Гэндальф',result['message'])
        followup=await self.ask('только онлайн',result['context'])
        self.assertEqual(followup['context']['terms'],['python'])
        self.assertEqual(followup['context']['age_min'],16)
        addressed=await self.ask('Гэндальф найди бесплатные курсы по Linux онлайн')
        self.assertEqual(addressed['context']['terms'],['linux'])
        self.assertEqual([item['title'] for item in addressed['results']],['Linux basics'])

    async def test_gandalf_identity_uses_the_conversation_language(self):
        await self.register()
        for phrase,locale in [('Привіт Ґандальф','uk'),('Hello Gandalf','en'),('Привет Гэндальф','ru')]:
            result=await self.ask(phrase)
            self.assertEqual(result['kind'],'wizard')
            self.assertEqual(result['context']['language'],locale)

    async def test_invalid_age_is_a_clarification_not_a_server_error(self):
        await self.seed()
        for value in ('мне 11','мне 101','курсы для 17-14 лет'):
            result=await self.ask(value)
            self.assertEqual(result['kind'],'invalid_age')
            self.assertEqual(result['results'],[])

for name in list(APITests.__dict__):
    if name.startswith('test_'): setattr(AssistantTests,name,None)

def load_tests(loader,tests,pattern): return loader.loadTestsFromTestCase(AssistantTests)
