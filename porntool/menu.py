import logging

import urwid

from porntool import db
from porntool import girl
from porntool import tag

logger = logging.getLogger(__name__)

def iterFind(itr, pred):
    return next((i for i, x in enumerate(itr) if pred(x)), None)

class QuestionBox(urwid.Edit):
    def __init__(self, onEnter, onEsc, *args, **kwargs):
        self.onEnter = onEnter
        self.onEsc = onEsc
        super(QuestionBox, self).__init__(*args, **kwargs)

    def keypress(self, size, key):
        if key == 'enter':
            self.onEnter()
        elif key == 'esc':
            self.onEsc()
        return super(QuestionBox, self).keypress(size, key)

class MenuButton(urwid.Button):
    def __init__(self, shortcut, text, callback):
        self.shortcut = shortcut
        self.text = text
        super(MenuButton, self).__init__(text, callback)


class Menu(urwid.ListBox):
    def __init__(self, title, buttons, *args, **kwds):
        body = [urwid.Text(title), urwid.Divider()]
        for button in buttons:
            body.append(urwid.AttrMap(button, None, focus_map='reversed'))
        self.buttons = buttons
        super(Menu, self).__init__(urwid.SimpleFocusListWalker(body), *args, **kwds)

    def keypress(self, size, key):
        # this probably won't work if scrolling is involved
        # when that happens - look at the ListBox source code
        p = iterFind(self.buttons, lambda x: x.shortcut == key)
        if p is not None:
            p += 2 # make space for the title and the divider
            self.change_focus(size, p)
        else:
            super(Menu, self).keypress(size, key)

    def setTitle(self, title):
        self.body[0].set_text(title)

class FileEditor(urwid.ListBox):
    def __init__(self, title, question_box):
        body = [urwid.Text(title), urwid.Divider(), question_box]
        super(FileEditor, self).__init__(urwid.SimpleListWalker(body))

class FileMenuPadding(urwid.Padding):
    def __init__(self, filepath, rating):
        self.filepath = filepath
        self.rating = rating
        self.file_ = filepath.pornfile
        self.title = filepath.filename()
        self.same_movie = False
        tags = " ".join([t.tag for t in self.file_.tags])
        girls = " ".join([g.name for g in self.file_.girls])
        self._r = rating.getRating(filepath.pornfile)
        self.buttons = [MenuButton('g', 'Girls: {}'.format(girls), self.editGirls),
                        MenuButton('t', 'Tags: {}'.format(tags), self.editTags),
                        MenuButton('r', 'Rating: {}'.format(self._r), self.changeRating),
                        MenuButton('e', 'Replay', self.sameMovie),
                        MenuButton('n', 'Next', self.nextFile),
                        MenuButton('q', 'Quit', self.quit)]
        self.menu = Menu(self.title, self.buttons)
        urwid.Padding.__init__(self, self.menu, left=2, right=2)

    def editGirls(self, button):
        def done():
            girl_text = edit.edit_text.split()
            new_girls = [girl.getGirl(g) for g in girl_text]
            self.file_.girls = new_girls
            self.buttons[0].set_label('Girls: {}'.format(edit.edit_text))
            self.toMain()
        girls = " ".join([g.name for g in self.file_.girls])
        edit = QuestionBox(done, self.toMain, 'Edit girls: ', girls)
        fe = FileEditor(self.title, edit)
        self.original_widget = fe

    def sameMovie(self, button):
        self.same_movie = True
        urwid.emit_signal(self, 'done', self)

    def nextFile(self, button):
        urwid.emit_signal(self, 'done', self)

    def editTags(self, button):
        tags = " ".join([t.tag for t in self.file_.tags])
        def done():
            tag_text = edit.edit_text.split()
            new_tags = [tag.getTag(t) for t in tag_text]
            self.file_.tags = new_tags
            self.buttons[1].set_label('Tags: {}'.format(edit.edit_text))
            self.toMain()
        edit = QuestionBox(done, self.toMain, 'Edit tags: ', tags)
        fe = FileEditor(self.title, edit)
        self.original_widget = fe

    def toMain(self, *args):
        db.getSession().commit()
        self.original_widget = self.menu

    def changeRating(self, button):
        def done():
            try:
                new_r = int(edit.edit_text)
                if new_r != self._r:
                    self.rating.setRating(self.filepath.pornfile, new_r)
                    self._r = new_r
                    self.buttons[2].set_label('Rating: {}'.format(new_r))
            except:
                logger.exception('Failed to set rating')
            finally:
                self.toMain()
        edit = QuestionBox(done, self.toMain, 'New Rating: ', str(self._r))
        fe = FileEditor(self.title, edit)
        self.original_widget = fe

    def exitProgram(self, button):
        db.getSession().commit()
        raise urwid.ExitMainLoop()

    def quit(self, button):
        response = urwid.Text(u'Are you sure you want to quit?')
        yes = urwid.Button(u'Yes')
        no = urwid.Button(u'No')
        urwid.connect_signal(yes, 'click', self.exitProgram)
        urwid.connect_signal(no, 'click', self.toMain)
        self.original_widget = urwid.Padding(urwid.ListBox(urwid.SimpleFocusListWalker(
            [response, urwid.AttrMap(yes, None, focus_map='reversed'),
             urwid.AttrMap(no, None, focus_map='reversed')])))

urwid.register_signal(FileMenuPadding, ['done'])
