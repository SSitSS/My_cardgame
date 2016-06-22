Описание веб-приложения "Битва магов"
=====================================

Правила игры
------------

Каждый игрок является магом с собственным набором карт заклинаний, хранящихся
в его колоде. На руке у каждого игрока постоянно присутствует 3 карты.
Карта выдается игроку сразу после того, как он разыграет одну из
имеющихся карт, кроме тех случаев, когда карт в колоде больше не осталось.

Изначально каждый игрок начинает с 25 очками здоровья и запасом маны, равным 5,
каждый ход запас маны увеличивается на 3. Для того, чтобы разыграть карту,
игроку нужно одну из имеющихся карт перетащить в красное поле, после чего
она выполнит действие, написанное на ней, если у игрока будет хватать маны.
Если нет, то она "перевернется" и будет показываться оппоненту. Для передачи
хода оппоненту игрок может нажать на красное поле.

Игра заканчивается, если один из игроков выйдет из игры или будет иметь неположительное число очков здоровья. Кроме того, если у обоих игроков
заканчиваются карты, то победившимся считается тот, кто имеет больше очков
здоровья (при равном числе игра оканчивается ничьей).

Общая структура веб-приложения
------------------------------

Сайт состоит из трёх основных страниц:
- для создания и выбора поединка;
- для участия в поединке;
- для редактирования колоды, которая используется в поединках.

Кроме того, есть страница для регистрации игрока. Используется стандартный
механизм фреймворка Django для авторизации пользователей (модуль django.contrib.auth).

Страница для создания и выбора поединка
---------------------------------------

Можно создать игру или присоединиться к уже созданной.

В списке созданных игр отображаются только игры, которые ещё не завершились. При попытке присоединения к уже начатой игре и при других подобных действиях пользователь перенаправляется на страницу создания и выбора поединка.

Каждый игрок может участвовать не более чем в одной игре в каждый момент.

При присоединении к игре открывается страница поединка.

Страница поединка
-----------------

Страница поединка содержит игровое поле для игры по вышеописанным правилам. Также в нижней части страницы находится поле внутриигрового чата.

Для предотвращения нарушения правил игры основая часть логики игры (модель приложения в терминологии парадигмы MVC) реализована в серверной части. В клиентской части находятся control- и view-компоненты.

Взаимодействие между клиентской и серверной частью реализуется на данной странице
посредством веб-сокетов (используется Django-модуль django-websocket-redis). Клиентская часть отправляет JSON-пакет серверу при действии игрока (перемещение карты, передача хода другому игроку, завершение игры и т.д.). Сервер вырабатывает ответ на действие и может передать его как игроку, который совершил действие, так и другому игроку.

Для каждой игры создаётся объект, хранящий состояние об игре и вырабатывающий ответы, поэтому функционально число одновременных игр неограничено.

Основной библиотекой, используемой в клиентской части для отображения состояния игры, является CreateJS. Происходит отображение всех действий противника, в том числе перекладывание карт в реальном времени.

Страница редактирования колоды
------------------------------

На странице редактирования колоды расположены два поля:
- поле с картами, которые можно добавить в колоду;
- поле с картами, которые уже есть в колоде.

При изменении состояния поля с картами, которые уже есть в колоде, это состояние сохраняется на сервере автоматически.

Изначально с каждым зарегистрировавшимся игроком ассоциируется стандартная колода, состоящая из двух карт каждого из десяти возможных типов (всего в колоде может быть до трёх карт каждого типа).

Запуск веб-приложения на сервере
--------------------------------

cd examples
sudo pip install -r requirements.txt
python manage.py runserver

В браузере: http://127.0.0.1:8000/

