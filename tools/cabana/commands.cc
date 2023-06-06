#include <QApplication>

#include "tools/cabana/commands.h"

// EditMsgCommand

EditMsgCommand::EditMsgCommand(const MessageId &id, const QString &name, int size, const QString &comment, QUndoCommand *parent)
    : id(id), new_name(name), new_size(size), new_comment(comment), QUndoCommand(parent) {
  if (auto msg = dbc()->msg(id)) {
    old_name = msg->name;
    old_size = msg->size;
    old_comment = msg->comment;
    setText(QObject::tr("edit message %1:%2").arg(name).arg(id.address));
  } else {
    setText(QObject::tr("new message %1:%2").arg(name).arg(id.address));
  }
}

void EditMsgCommand::undo() {
  if (old_name.isEmpty())
    dbc()->removeMsg(id);
  else
    dbc()->updateMsg(id, old_name, old_size, old_comment);
}

void EditMsgCommand::redo() {
  dbc()->updateMsg(id, new_name, new_size, new_comment);
}

// RemoveMsgCommand

RemoveMsgCommand::RemoveMsgCommand(const MessageId &id, QUndoCommand *parent) : id(id), QUndoCommand(parent) {
  if (auto msg = dbc()->msg(id)) {
    message = *msg;
    setText(QObject::tr("remove message %1:%2").arg(message.name).arg(id.address));
  }
}

void RemoveMsgCommand::undo() {
  if (!message.name.isEmpty()) {
    dbc()->updateMsg(id, message.name, message.size, message.comment);
    for (auto s : message.getSignals())
      dbc()->addSignal(id, *s);
  }
}

void RemoveMsgCommand::redo() {
  if (!message.name.isEmpty())
    dbc()->removeMsg(id);
}

// AddSigCommand

AddSigCommand::AddSigCommand(const MessageId &id, const cabana::Signal &sig, QUndoCommand *parent)
    : id(id), signal(sig), QUndoCommand(parent) {
  setText(QObject::tr("add signal %1 to %2:%3").arg(sig.name).arg(msgName(id)).arg(id.address));
}

void AddSigCommand::undo() { dbc()->removeSignal(id, signal.name); }
void AddSigCommand::redo() { dbc()->addSignal(id, signal); }

// RemoveSigCommand

RemoveSigCommand::RemoveSigCommand(const MessageId &id, const cabana::Signal *sig, QUndoCommand *parent)
    : id(id), signal(*sig), QUndoCommand(parent) {
  setText(QObject::tr("remove signal %1 from %2:%3").arg(signal.name).arg(msgName(id)).arg(id.address));
}

void RemoveSigCommand::undo() { dbc()->addSignal(id, signal); }
void RemoveSigCommand::redo() { dbc()->removeSignal(id, signal.name); }

// EditSignalCommand

EditSignalCommand::EditSignalCommand(const MessageId &id, const cabana::Signal *sig, const cabana::Signal &new_sig, QUndoCommand *parent)
    : id(id), old_signal(*sig), new_signal(new_sig), QUndoCommand(parent) {
  setText(QObject::tr("edit signal %1 in %2:%3").arg(old_signal.name).arg(msgName(id)).arg(id.address));
}

void EditSignalCommand::undo() { dbc()->updateSignal(id, new_signal.name, old_signal); }
void EditSignalCommand::redo() { dbc()->updateSignal(id, old_signal.name, new_signal); }

namespace UndoStack {

QUndoStack *instance() {
  static QUndoStack *undo_stack = new QUndoStack(qApp);
  return undo_stack;
}

}  // namespace UndoStack
