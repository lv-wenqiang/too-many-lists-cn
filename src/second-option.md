# Using Option

特别注意的读者可能已经注意到我们实际上重新发明了
一个非常糟糕的Option版本：

```rust ,ignore
enum Link {
    Empty,
    More(Box<Node>),
}
```

链接仅为`Option<Box<Node>>`。现在，不必写信
`Option<Box<Node>>`无处不在，与`pop`不同，我们不会公开这个
到外面的世界，所以也许没关系。然而， Option有一些*真的
nice *我们自己手动实现的方法。让我们*不要*
执行此操作，并将所有内容替换为“选项”。首先，我们会天真地做
只需将所有内容重命名为使用Some和None ：

```rust ,ignore
use std::mem;

pub struct List {
    head: Link,
}

// yay type aliases!
type Link = Option<Box<Node>>;

struct Node {
    elem: i32,
    next: Link,
}

impl List {
    pub fn new() -> Self {
        List { head: None }
    }

    pub fn push(&mut self, elem: i32) {
        let new_node = Box::new(Node {
            elem: elem,
            next: mem::replace(&mut self.head, None),
        });

        self.head = Some(new_node);
    }

    pub fn pop(&mut self) -> Option<i32> {
        match mem::replace(&mut self.head, None) {
            None => None,
            Some(node) => {
                self.head = node.next;
                Some(node.elem)
            }
        }
    }
}

impl Drop for List {
    fn drop(&mut self) {
        let mut cur_link = mem::replace(&mut self.head, None);
        while let Some(mut boxed_node) = cur_link {
            cur_link = mem::replace(&mut boxed_node.next, None);
        }
    }
}
```

这稍微好一点，但大赢家将来自Option的方法。

首先， `mem::replace(&mut option, None)`是一个令人难以置信的
option实际上只是一种方法： `take`。

```rust ,ignore
pub struct List {
    head: Link,
}

type Link = Option<Box<Node>>;

struct Node {
    elem: i32,
    next: Link,
}

impl List {
    pub fn new() -> Self {
        List { head: None }
    }

    pub fn push(&mut self, elem: i32) {
        let new_node = Box::new(Node {
            elem: elem,
            next: self.head.take(),
        });

        self.head = Some(new_node);
    }

    pub fn pop(&mut self) -> Option<i32> {
        match self.head.take() {
            None => None,
            Some(node) => {
                self.head = node.next;
                Some(node.elem)
            }
        }
    }
}

impl Drop for List {
    fn drop(&mut self) {
        let mut cur_link = self.head.take();
        while let Some(mut boxed_node) = cur_link {
            cur_link = boxed_node.next.take();
        }
    }
}
```

其次， `match option { None => None, Some(x) => Some(y) }`就是这样一个
令人难以置信的常用成语，它被称为`map`。`map`采用函数
在`Some(x)`中的`x`上执行，在`Some(y)`中生成`y`。我们可以
写一个合适的`fn`并将其传递给`map` ，但我们更愿意写
做*内联*。

要做到这一点，方法是使用*闭包*。闭包是匿名函数，
额外的超能力：他们可以引用闭包*外部*的局部变量！
这使得它们对于执行各种条件逻辑非常有用。
我们只做`match`的地方在`pop` ，所以让我们重写一下：

```rust ,ignore
pub fn pop(&mut self) -> Option<i32> {
    self.head.take().map(|node| {
        self.head = node.next;
        node.elem
    })
}
```

啊，好多了。让我们确保我们没有破坏任何东西：

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 2 tests
test first::test::basics ... ok
test second::test::basics ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured

```

太好了！让我们继续实际改进代码的*行为*。
