# -*- coding: utf-8 -*-
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django import forms
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from datetime import *
from random import *
from ws4redis.publisher import RedisPublisher
from ws4redis.redis_store import RedisMessage

"""
TODO:

Желательно:
- Play Game:
	- чат:
		- выв. инф. о подкл. игр. (в самом нач. и при нов. подкл.)
	- сообщения об ошибках (нет места в поединке и т.д.)
	- ускор.
		- чтобы меньше тормоз.
		- чтобы выд. 100 боёв
	- отобр. назв. игры
- отобр. сост. игры (начата, завершена ли, кто выиграл)
"""

class Username2Cards:
	def __init__(self):
		self.username2cards = {}

	def get(self, username):
		if username not in self.username2cards:
			default_deck_ids = list(range(20))
			self.username2cards[username] = default_deck_ids
		return self.username2cards[username]

	def set(self, username, cards):
		self.username2cards[username] = cards

username2cards = Username2Cards()


class Username2Gameid:
	def __init__(self):
		self.username2gameid = {}

	def get(self, username):
		if username not in self.username2gameid:
			self.username2gameid[username] = None
		return self.username2gameid[username]

	def set(self, username, gameid):
		self.username2gameid[username] = gameid

username2gameid = Username2Gameid()


gameid2gamename = {1: 'igra1'}
gamename2gameid = {'igra1': 1}
last_game_id = {'last': 1}


def send(username, sending):
	redis_publisher = RedisPublisher(facility='foobar', users=username)
	print 'answer_client: sending to ' + username + ': ' + sending
	redis_publisher.publish_message(sending)

class Answerer:
	card_types = [
				# M  D  H
				[5, 6, 0],
				[1, 1, 0],
				[7, 9, 0],
				[10, 15, 0],
				[2, 3, 0],
				[3, 4, 0],
				[2, 0, 3],
				[4, 0, 5],
				[4, 2, 2],
				[7, 4, 4]]

	def __init__(self, players_usernames):
		assert(len(players_usernames) == 2)

		self.initialized = False
		self.finished = False
		self.usernames = players_usernames

		self.decks_ids = []
		for i in range(2):
			username = self.usernames[i]
			cards = username2cards.get(username)
			self.decks_ids.append(cards)

		Answerer.card_values = []
		self.card_ids_shuffled = list(range(0, 30))
		shuffle(self.card_ids_shuffled)
		print "shuffle:", self.card_ids_shuffled
		self.user2sendings = {}
		for i in range(30):
			Answerer.card_values += [Answerer.card_types[i % 10] + [i]]

	def set_cards(self, username, cards):
		for i in range(len(self.usernames)):
			if self.usernames[i] == username:
				self.decks_ids[i] = cards
				return
		assert(False)

	def finish(self):
		for username in self.usernames:
			username2gameid.set(username, None)
		self.finished = True

	def restart(self):
		print 'Answerer: restarting'
		print('Answerer.card_values: ' + str(Answerer.card_values))
		print('self.decks_ids: ' + str(self.decks_ids))

		self.turn = 0
		self.player_hps = [25, 25]
		self.player_manas = [5, 5]
		self.mana_regen = 3

		self.player_decks = []
		self.player_hands = [[],[]]
		for player in range(2):
			player_card_values = []
			for id_ in self.decks_ids[player]:
				player_card_values += [Answerer.card_values[id_]]
			print(player_card_values)
			self.player_decks += [player_card_values]
			for i in range(min(3, len(self.player_decks[player]))):
				self.pick_a_card(self.player_decks[player], self.player_hands[player])

		print(self.player_hands)
		self.initialized = True

	def pick_a_card(self, player_deck, player_hand):
		A = randint(0, len(player_deck) - 1)
		new_card = player_deck.pop(A)
		player_hand += [new_card]
		
	def answer_client(self, post, requester_username):
		self.make_response(post, requester_username)
		
		if self.response['type'] == 'old_sendings':
			username = self.response['to_user']
			if username not in self.user2sendings:
				self.user2sendings[username] = []
			for x in self.user2sendings[username]:
				send(username, x)
			return

		if self.response['type'] == 'chat_message':
			print('chat_message to users', self.response['to_users'])
			for username in self.response['to_users']:
				message = self.response['chat_message']
				from_user = self.response['from_user']
				json = JsonResponse({'msg_type': 'chat_message',
				                   	 'from_user': from_user,
				                   	 'chat_message': message,
				                   	 'date': str(datetime.now())
								 	 })
				sending = RedisMessage(json.content)
				send(username, sending)
			return

		if self.response['type'] == 'move_xy':
			username = self.response['to_user']
			json = JsonResponse({'msg_type': 'move_xy',
			                     'card_ids': self.response['card_ids'],
			                     'xs': self.response['xs'], 'ys': self.response['ys'],
				                 'date': str(datetime.now())
								 })
			sending = RedisMessage(json.content)
			if username not in self.user2sendings:
				self.user2sendings[username] = []
			self.user2sendings[username].append(sending)
			send(username, sending)
			return
		
		for cur in range(2):
			enemy = (cur + 1) % 2

			your_status = "You have " + str(self.player_hps[cur]) + " hp"
			your_status += " and " + str(self.player_manas[cur]) + " mana\n"
			enemy_status = "Enemy have " + str(self.player_hps[enemy]) + " hp"
			enemy_status += " and " + str(self.player_manas[enemy]) + " mana\n"

			cards = ''
			hand_card_ids = []
			hand = self.player_hands[cur]
			for i in range(len(hand)):
				cards += str(i + 1) + ". Manacost = " + str(hand[i][0])
				cards += ", Damage = " + str(hand[i][1])
				cards += ", Heal = " + str(hand[i][2]) + '\n'
				hand_card_ids.append(hand[i][-1])

			to_do = "Enter number of card you wish to play or write 'pass' if you want to pass your turn"
			comment = your_status + enemy_status + cards + to_do

			if cur == self.turn:
				answer_text = self.response['to_current_player']
				disclose_card_id = -1
				disclose_card_id_shuffled = -1
			else:
				answer_text = self.response['to_waiting_player']
				disclose_card_id = self.response['disclose_card_id']
				disclose_card_id_shuffled = self.response['disclose_card_id_shuffled']

			username = self.usernames[cur]
			json = JsonResponse({'msg_type': 'info',
			                     'comment': comment,
				                   'your_hp': self.player_hps[cur],
				                   'enemy_hp': self.player_hps[enemy],
				                   'your_mana': self.player_manas[cur],
				                   'enemy_mana': self.player_manas[enemy],
				                   'your_deck_size': len(self.player_decks[cur]),
				                   'enemy_deck_size': len(self.player_decks[enemy]),
				                   'info': answer_text,
				                   'date': str(datetime.now()),
				                   'hand_card_ids': hand_card_ids,
								   'disclose_card_id': disclose_card_id,
								   'disclose_card_id_shuffled': disclose_card_id_shuffled
								   })
			sending = RedisMessage(json.content)
			send(username, sending)

	def make_response(self, post, requester_username):
		self.response = {}
		
		user_from = requester_username
		is_message_from_current_player = (self.usernames[self.turn] == user_from)
		enemy = (self.turn + 1) % 2
		
		msg_type = post.get('msg_type')
		print('make_response: msg_type =', msg_type)
			
		if msg_type == 'request_old_sendings':
			self.response['type'] = 'old_sendings'
			self.response['to_user'] = user_from
			return

		if msg_type == 'chat_message':
			self.response['type'] = 'chat_message'
			self.response['from_user'] = user_from
			self.response['to_users'] = self.usernames
			self.response['chat_message'] = post.get('chat_message')
			return
			
		if msg_type == 'moved_xy':
			card_ids = map(lambda cid: self.card_ids_shuffled[int(cid)], list(post.getlist('card_ids[]')))
			xs = map(int, list(post.getlist('xs[]')))
			ys = map(lambda y: 700 - int(y), list(post.getlist('ys[]')))
			print 'card_ids:', card_ids
			print 'xs:', xs
			print 'ys:', ys
			self.response['type'] = 'move_xy'
			self.response['card_ids'] = card_ids
			self.response['xs'] = xs
			self.response['ys'] = ys
			if is_message_from_current_player:
				to = self.usernames[enemy]
			else:
				to = self.usernames[self.turn]
			self.response['to_user'] = to
			return

		self.response['type'] = ''
		self.response['to_current_player'] = ''
		self.response['to_waiting_player'] = ''
		self.response['disclose_card_id'] = -1
		self.response['disclose_card_id_shuffled'] = -1
			
		message = post.get('message')
		print 'message:', message
		
		if not is_message_from_current_player and message != 'leave':
			self.response['to_waiting_player'] = 'Not your turn'
			return
		
		if message == 'restart':
			self.restart()
			self.response['to_current_player'] = 'Game restarted'
			self.response['to_waiting_player'] = 'Game restarted'
			return

		if message == 'pass':
			self.player_manas[enemy] += self.mana_regen
			self.turn = (self.turn + 1) % 2
			self.response['to_current_player'] = 'Now your turn'
			return

		if message not in ['1', '2', '3', 'leave']:
			self.response['to_current_player'] = 'Enter card num or write pass'
			return

		if message == 'leave':
			if is_message_from_current_player:
				self.player_hps[self.turn] = 0
			else:
				self.player_hps[enemy] = 0

		else:
			num = int(message) - 1
			if num > len(self.player_hands[self.turn]) - 1:
				self.response['to_current_player'] = 'Enter less num'
				return
				
			self.response['disclose_card_id'] = int(post.get('card_id'))
			self.response['disclose_card_id_shuffled'] = self.card_ids_shuffled[self.response['disclose_card_id']]

			if self.player_hands[self.turn][num][0] > self.player_manas[self.turn]:
				self.response['to_current_player'] = 'Not enough mana'
				return

			card = self.player_hands[self.turn].pop(num)
			self.player_manas[self.turn] -= card[0]
			self.player_hps[enemy] -= card[1]
			self.player_hps[self.turn] += card[2]
			if len(self.player_decks[self.turn]) > 0:
				self.pick_a_card(self.player_decks[self.turn], self.player_hands[self.turn])
			self.response['to_waiting_player'] = 'Enemy damaged you by ' + str(card[1]) + ' and healed himself by ' + str(card[2]) + '\n'

		if self.player_hps[self.turn] <= 0:
			self.response['to_waiting_player'] += 'You Won!!!\n'
			self.response['to_current_player'] += 'You Lost(\n'
			self.finish()
			return

		if self.player_hps[enemy] <= 0:
			self.response['to_current_player'] += 'You Won!!!\n'
			self.response['to_waiting_player'] += 'You Lost(\n'
			self.finish()
			return

		#if len(self.player_hands[enemy]) == 0 and len(self.player_hands[self.turn]) == 0:
		if len(self.player_hands[enemy]) == 0 or len(self.player_hands[self.turn]) == 0:
			if self.player_hps[self.turn] > self.player_hps[enemy]:
				self.response['to_current_player'] += 'You Won!!!\n'
				self.response['to_waiting_player'] += 'You Lost(\n'
			elif self.player_hps[self.turn] < self.player_hps[enemy]:
				self.response['to_waiting_player'] += 'You Won!!!\n'
				self.response['to_current_player'] += 'You Lost(\n'
			else:
				self.response['to_waiting_player'] += 'Draw!!!\n'
				self.response['to_current_player'] += 'Draw!!!\n'
			self.finish()
			return


class RegisterView(TemplateView):
	template_name = 'register.html'
	def get(self, request, *args, **kwargs):
		form = UserCreationForm()
		return render(request, "register.html", {
			'form': form,
		})
	def post(self, request, *args, **kwargs):
		form = UserCreationForm(request.POST)
		if form.is_valid():
			new_user = form.save()
			return HttpResponseRedirect("/choose_game/")
		return HttpResponse('Form was not valid')


class ChooseGameView(TemplateView):
	template_name = 'choose_game.html'

	def get(self, request, *args, **kwargs):
		return render(request, "choose_game.html", {
			'gameid2gamename': gameid2gamename,
		})

	def post(self, request, *args, **kwargs):
		game_name = request.POST.get('game_name')
		if game_name in gamename2gameid:
			err_msg = 'A game with the same name (' + game_name + ') already exists'
			return HttpResponse(err_msg)
		last_game_id['last'] += 1
		gameid2gamename[last_game_id['last']] = game_name
		gamename2gameid[game_name] = last_game_id['last']
		return HttpResponseRedirect('/play_game/?game_id=' + str(last_game_id['last']))


#answerer = Answerer(['petya', 'vasya'])

class PlayGameView(TemplateView):
	template_name = 'play_game.html'
	game_id_to_players = {}
	game_id_to_answerer = {}

	def __init__(self):
		#if not answerer.initialized:
		#	answerer.restart()
		return super(PlayGameView, self).__init__()

	def get_context_data(self, **kwargs):
		context = super(PlayGameView, self).get_context_data(**kwargs)
		context.update(users=User.objects.all())
		return context

	@csrf_exempt
	def dispatch(self, *args, **kwargs):
		return super(PlayGameView, self).dispatch(*args, **kwargs)

	def get(self, request, *args, **kwargs):
		if not request.user.is_authenticated():
			return HttpResponseRedirect("/register/")

		username = request.user.username

		game_id_already = username2gameid.get(username)
		game_id = request.GET.get('game_id', None)
		if game_id is not None:
			game_id = int(game_id)
		print 'PlayGameView.get: game_id =', game_id
		if game_id_already is not None and game_id != game_id_already:
			return HttpResponseRedirect("/play_game/?game_id=" + str(game_id_already))

		if game_id is None:
			print "game_id is None"
			return HttpResponseRedirect("/choose_game/")

		game_id = int(game_id)
		if game_id not in gameid2gamename:
			print gameid2gamename
			return HttpResponseRedirect("/choose_game/")

		if game_id not in PlayGameView.game_id_to_players:
			PlayGameView.game_id_to_players[game_id] = []
		players_usernames = PlayGameView.game_id_to_players[game_id]

		if username not in players_usernames:
			if len(players_usernames) >= 2:
				return HttpResponseRedirect("/choose_game/")
			players_usernames.append(username)
			username2gameid.set(username, game_id)

		if len(players_usernames) == 2:
			if game_id not in PlayGameView.game_id_to_answerer:
				answerer = Answerer(players_usernames)
				answerer.restart()
				PlayGameView.game_id_to_answerer[game_id] = answerer

		print PlayGameView.game_id_to_players[game_id]

		return render(request, PlayGameView.template_name, {
			'players_usernames': players_usernames,
			'game_id': game_id,
		})

	def post(self, request, *args, **kwargs):
		print request.POST

		if not request.user.is_authenticated():
			return HttpResponseRedirect("/register/")

		game_id = request.POST.get('game_id', None)
		print 'PlayGameView.post: game_id =', game_id
		if game_id is None:
			return HttpResponseRedirect("/choose_game/")

		game_id = int(game_id)
		if game_id not in PlayGameView.game_id_to_answerer:
			return HttpResponseRedirect("/choose_game/")

		username = request.user.username
		if game_id != username2gameid.get(username):
			return HttpResponseRedirect("/choose_game/")

		answerer = PlayGameView.game_id_to_answerer[game_id]
		answerer.answer_client(request.POST, username)

		if answerer.finished:
			del PlayGameView.game_id_to_answerer[game_id]
			game_name = gameid2gamename[game_id]
			del gameid2gamename[game_id]
			del gamename2gameid[game_name]

		return HttpResponse('OK')


class DeckEditorView(TemplateView):
	template_name = 'deck_editor.html'

	def get_context_data(self, **kwargs):
		context = super(DeckEditorView, self).get_context_data(**kwargs)
		context.update(users=User.objects.all())
		return context

	@csrf_exempt
	def dispatch(self, *args, **kwargs):
		return super(DeckEditorView, self).dispatch(*args, **kwargs)

	def get(self, request, *args, **kwargs):
		if not request.user.is_authenticated():
			return HttpResponseRedirect("/register/")
		username = request.user.username

		return render(request, DeckEditorView.template_name, {
			'cards_initial': str(username2cards.get(username))
		})

	def post(self, request, *args, **kwargs):
		if not request.user.is_authenticated():
			return HttpResponseRedirect("/register/")

		username = request.user.username

		cards_str = request.POST.get('cards')
		cards = list(int(x) for x in cards_str.split(','))

		print('cards of user ' + username + ': ' + str(username2cards.get(username)) + ' -> ' + str(cards))

		username2cards.set(username, cards)

		return HttpResponse('OK')
