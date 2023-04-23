#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
cd $DIR

RC_FILE="${HOME}/.$(basename ${SHELL})rc"
if [ "$(uname)" == "Darwin" ] && [ $SHELL == "/bin/bash" ]; then
  RC_FILE="$HOME/.bash_profile"
fi

if ! command -v "pyenv" > /dev/null 2>&1; then
  echo "pyenv install ..."
  curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash

  echo -e "\n. ~/.pyenvrc" >> $RC_FILE
  cat <<EOF > "${HOME}/.pyenvrc"
if [ -z "\$PYENV_ROOT" ]; then
  export PATH=\$HOME/.pyenv/bin:\$HOME/.pyenv/shims:\$PATH
  export PYENV_ROOT="\$HOME/.pyenv"
  eval "\$(pyenv init -)"
  eval "\$(pyenv virtualenv-init -)"
fi
EOF

  # setup now without restarting shell
  export PATH=$HOME/.pyenv/bin:$HOME/.pyenv/shims:$PATH
  export PYENV_ROOT="$HOME/.pyenv"
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
fi

export MAKEFLAGS="-j$(nproc)"

PYENV_PYTHON_VERSION=$(cat .python-version)
if ! pyenv prefix ${PYENV_PYTHON_VERSION} &> /dev/null; then
  # no pyenv update on mac
  if [ "$(uname)" == "Linux" ]; then
    echo "pyenv update ..."
    pyenv update
  fi
  echo "python ${PYENV_PYTHON_VERSION} install ..."
  CONFIGURE_OPTS="--enable-shared" pyenv install -f ${PYENV_PYTHON_VERSION}
fi
eval "$(pyenv init --path)"

echo "update pip"
pip install pip==22.3.1
pip install poetry==1.2.2

poetry config virtualenvs.prefer-active-python true --local

if [[ -n "$XX" ]] || [[ "$(basename "$(dirname "$(pwd)")")" == "xx" ]]; then
  XX=true
fi

POETRY_INSTALL_ARGS="--no-cache --no-root"

if [ -n "$XX" ]; then
  echo "WARNING: using xx dependency group, installing globally"
  poetry config virtualenvs.create false --local
  POETRY_INSTALL_ARGS="$POETRY_INSTALL_ARGS --with xx --sync"
else
  echo "PYTHONPATH=${PWD}" > .env
  poetry self add poetry-dotenv-plugin@^0.1.0
fi

echo "pip packages install..."
poetry install $POETRY_INSTALL_ARGS
pyenv rehash

[ -n "$XX" ] || [ -n "$POETRY_VIRTUALENVS_CREATE" ] && RUN="" || RUN="poetry run"

if [ "$(uname)" != "Darwin" ]; then
  echo "pre-commit hooks install..."
  shopt -s nullglob
  for f in .pre-commit-config.yaml */.pre-commit-config.yaml; do
    cd $DIR/$(dirname $f)
    if [ -e ".git" ]; then
      $RUN pre-commit install
    fi
  done
fi
