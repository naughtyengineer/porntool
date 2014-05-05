import logging

import urwid

from porntool import db
from porntool import girl
from porntool import tag
from porntool import widget

logger = logging.getLogger(__name__)

def iterFind(itr, pred):
    return next((i for i, x in enumerate(itr) if pred(x)), None)

class QuestionBox(urwid.Edit):
    def __init__(self, onEnter, onEsc, *args, **kwargs):
        self.onEnter = onEnter
        self.onEsc = onEsc
        urwid.Edit.__init__(self, *args, **kwargs)

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
        urwid.ListBox.__init__(self, urwid.SimpleFocusListWalker(body), *args, **kwds)

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
        urwid.ListBox.__init__(self, urwid.SimpleListWalker(body))


class MenuPadding(urwid.Padding, widget.OnFinished, widget.LoopAware):
    def __init__(self, title, buttons):
        self.title = title
        self.buttons = buttons
        self.menu = Menu(self.title, self.buttons)
        self.same_movie = False
        urwid.Padding.__init__(self, w=self.menu, left=2, right=2)
        widget.OnFinished.__init__(self)
        widget.LoopAware.__init__(self)

    def sameMovie(self, button):
        self.same_movie = True
        self.onFinished()

    def nextFile(self, button):
        self.onFinished()

    def editTags(self, button):
        tags = " ".join([t.tag for t in self.tagged.tags])
        def done():
            tag_text = edit.edit_text.split()
            new_tags = [tag.getTag(t) for t in tag_text]
            self.tagged.tags = new_tags
            self.tag_button.set_label('Tags: {}'.format(edit.edit_text))
            self.toMain()
        edit = QuestionBox(done, self.toMain, 'Edit tags: ', tags)
        fe = FileEditor(self.title, edit)
        self.original_widget = fe

    def toMain(self, *args):
        self.original_widget = self.menu

    def exitProgram(self, button):
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


class TagEditor(MenuPadding):
    def __init__(self, filepath):
        title = u"ID: {}, {}".format(filepath.file_id, filepath.path)
        self.tagged = filepath.pornfile
        tags = " ".join([t.tag for t in self.tagged.tags])
        self.tag_button = MenuButton('t', 'Tags: {}'.format(tags), self.editTags)
        buttons = [self.tag_button,
                   MenuButton('n', 'Next', self.nextFile),
                   MenuButton('q', 'Quit', self.quit)]
        super(TagEditor, self).__init__(title=title, buttons=buttons)


class ClipMenuPadding(MenuPadding):
    def __init__(self, clip, adjuster=None, title_prefix=''):
        filepath = clip.moviefile.getActivePath()
        active = [c for c in filepath.pornfile.clips if c.active]
        total = sum(c.duration for c in active)
        try:
            numer = len(active)
            denom = len(filepath.pornfile.clips)
        except ZeroDivisionError:
            fraction = 0.0
        title = u"{}{}: {} sec ({} total, {} / {})".format(
            title_prefix, filepath.path, clip.duration, total, numer, denom)
        tags = " ".join([t.tag for t in clip.tags])
        self.keep = True
        self.skip = False
        self.add = False
        self.tagged = clip
        self.clip = clip
        self.adjuster = adjuster
        self.tag_button = MenuButton('t', 'Tags: {}'.format(tags), self.editTags)
        buttons = [self.tag_button,
                   MenuButton('a', 'Adjust', self.adjust),
                   MenuButton('d', 'Delete', self.delete),
                   MenuButton('e', 'Replay', self.sameMovie),
                   MenuButton('s', 'Save', self.nextFile),
                   MenuButton('k', 'Skip Movie', self.skipMovie),
                   MenuButton('m', 'Add Movies', self.addMovies),
                   MenuButton('q', 'Quit', self.quit)]
        super(ClipMenuPadding, self).__init__(title=title, buttons=buttons)

    def addMovies(self, button):
        def done():
            self.add = int(qb.edit_text)
            self.nextFile(button)
        qb = QuestionBox(done, self.toMain, 'How Many Files: ', '10')
        fe = FileEditor(self.title, qb)
        self.original_widget = fe


    def delete(self, button):
        self.keep = False
        self.nextFile(button)

    def adjust(self, button):
        if self.adjuster:
            self.adjuster(self)

    def skipMovie(self, button):
        logger.debug('Skipping')
        self.skip = True
        self.nextFile(button)

class FileMenuPadding(MenuPadding):
    def __init__(self, filepath, rating):
        self.filepath = filepath
        self.rating = rating
        self.tagged = filepath.pornfile
        self.file_ = filepath.pornfile
        tags = " ".join([t.tag for t in self.file_.tags])
        girls = " ".join([g.name for g in self.file_.girls])
        self._r = rating.getRating(filepath.pornfile)
        self.tag_button = MenuButton('t', 'Tags: {}'.format(tags), self.editTags)
        title = filepath.path
        buttons = [MenuButton('g', 'Girls: {}'.format(girls), self.editGirls),
                   self.tag_button,
                   MenuButton('r', 'Rating: {}'.format(self._r), self.changeRating),
                   MenuButton('e', 'Replay', self.sameMovie),
                   MenuButton('n', 'Next', self.nextFile),
                   MenuButton('q', 'Quit', self.quit)]
        super(FileMenuPadding, self).__init__(title, buttons)

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
