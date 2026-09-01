# 实现游标

好了，我们只打算折腾 std 的 CursorMut，因为不可变的那个版本其实没什么意思。就像我最初的设计一样，它有一个包含 None 的“幽灵”元素，用来标示链表的起点／终点，而你可以“跨过它”绕到链表的另一头去。要实现它，我们需要：

* 一个指向当前节点的指针
* 一个指向链表的指针
* 当前索引

等等，当我们指向“幽灵”时索引是多少？

*皱眉* …… *查了查 std* …… *不喜欢 std 给的答案*

好吧，相当合理地，Cursor 上的`index`返回的是`Option<usize>`。std 的实现为了避免把它存成 Option 而做了一堆破事，可是……我们是链表啊，这没什么大不了的。另外 std 还有 cursor_front/cursor_back 那套东西，让游标从前端／后端元素开始，这感觉挺直观，但在链表为空时就不得不做点奇怪的处理。

你要是愿意可以把那些也实现出来，不过我打算砍掉所有重复的杂活和边角情形，只做一个从幽灵位置开始的、光秃秃的`cursor_mut`方法，大家可以用 move_next/move_prev 移到自己想要的位置（如果你真想要，再把它包装成 cursor_front 就行）。

我们开工吧：

```rust ,ignore
pub struct CursorMut<'a, T> {
    cur: Link<T>,
    list: &'a mut LinkedList<T>,
    index: Option<usize>,
}
```

相当直截了当，我们那个项目符号列表里的每一项对应一个字段！现在是`cursor_mut`方法：

```rust ,ignore
impl<T> LinkedList<T> {
    pub fn cursor_mut(&mut self) -> CursorMut<T> {
        CursorMut { 
            list: self, 
            cur: None, 
            index: None,
        }
    }
}
```

既然我们从幽灵位置开始，那就把所有东西都初始化成 None 就好，又漂亮又简单！接下来是移动：


```rust ,ignore
impl<'a, T> CursorMut<'a, T> {
    pub fn index(&self) -> Option<usize> {
        self.index
    }

    pub fn move_next(&mut self) {
        if let Some(cur) = self.cur {
            unsafe {
                // We're on a real element, go to its next (back)
                self.cur = (*cur.as_ptr()).back;
                if self.cur.is_some() {
                    *self.index.as_mut().unwrap() += 1;
                } else {
                    // We just walked to the ghost, no more index
                    self.index = None;
                }
            }
        } else if !self.list.is_empty() {
            // We're at the ghost, and there is a real front, so move to it!
            self.cur = self.list.front;
            self.index = Some(0)
        } else {
            // We're at the ghost, but that's the only element... do nothing.
        }
    }
}
```

这里有 4 种有意思的情形：

* 普通情形
* 普通情形，但我们抵达了幽灵
* 幽灵情形，此时我们移动到链表前端
* 幽灵情形，但链表是空的，于是什么都不做

move_prev 的逻辑一模一样，只是把 front/back 对调，索引的增减也反过来：

```rust ,ignore
pub fn move_prev(&mut self) {
    if let Some(cur) = self.cur {
        unsafe {
            // We're on a real element, go to its previous (front)
            self.cur = (*cur.as_ptr()).front;
            if self.cur.is_some() {
                *self.index.as_mut().unwrap() -= 1;
            } else {
                // We just walked to the ghost, no more index
                self.index = None;
            }
        }
    } else if !self.list.is_empty() {
        // We're at the ghost, and there is a real back, so move to it!
        self.cur = self.list.back;
        self.index = Some(self.list.len - 1)
    } else {
        // We're at the ghost, but that's the only element... do nothing.
    }
}
```

接下来我们加几个方法，用来查看游标周围的元素：current、peek_next 和 peek_prev。**一条非常重要的说明：**这些方法必须以`&mut self`借用我们的游标，而且结果必须与那次借用绑定。我们不能让用户拿到同一个可变引用的多份副本，也不能让他们在攥着这样一个引用时使用我们任何的插入／删除／分割／拼接 API！

谢天谢地，这正是你使用生命周期省略时 Rust 所做的默认假设，所以我们按默认行事就自然是对的！

```rust ,ignore
pub fn current(&mut self) -> Option<&mut T> {
    unsafe {
        self.cur.map(|node| &mut (*node.as_ptr()).elem)
    }
}

pub fn peek_next(&mut self) -> Option<&mut T> {
    unsafe {
        self.cur
            .and_then(|node| (*node.as_ptr()).back)
            .map(|node| &mut (*node.as_ptr()).elem)
    }
}

pub fn peek_prev(&mut self) -> Option<&mut T> {
    unsafe {
        self.cur
            .and_then(|node| (*node.as_ptr()).front)
            .map(|node| &mut (*node.as_ptr()).elem)
    }
}
```

脑子放空，现在全靠 Option 的各种方法和（此处省略的）编译器错误来思考。我原本对`Option<NonNull>`这套东西持怀疑态度，可是，天杀的，它真的让我能开着自动驾驶写这段代码。我在基于数组的集合上花了太多时间，那种地方你根本用不上 Option，哇这感觉真好！（`(*node.as_ptr())`还是很惨，不过，Rust 的原始指针就这德性……）

接下来我们有个选择：要么直接跳到 split 和 splice，也就是这套 API 的全部意义所在；要么先迈出一小步，做单个元素的 insert/remove。我有种预感，我们最后会想用 split 和 splice 来实现 insert/remove，所以……那就先做这两个，看看牌怎么落吧（我打这行字的时候是真的完全没底）。




# 分割

首先是 split_before 和 split_after，它们把当前元素之前／之后的所有内容作为一个 LinkedList 返回（在幽灵元素处停下；除非你本来就在幽灵位置，那样我们就直接返回整个链表，游标则指向一个空链表）：

*眯起眼睛*好吧，这个的逻辑确实不算平凡，所以我们得一步一步把它讲清楚。

对 split_before 来说，我看到有 4 种可能有意思的情形：

* 普通情形
* 普通情形，但 prev 是幽灵
* 幽灵情形，此时我们返回整个链表，自己变空
* 幽灵情形，但链表是空的，于是什么都不做，返回那个空链表

我们从边角情形开始。第三种情形我认为就是

```rust
mem::replace(self.list, LinkedList::new())
```

对吧？我们变空了，返回整个链表，而我们的字段本来就是 None，所以没什么要更新的。不错。哦嘿，这段代码在第四种情形下同样做对了事！

那么现在是普通情形……好吧，这个我需要画点 ASCII 图。在最一般的情形下，我们有这样的东西：

```text
list.front -> A <-> B <-> C <-> D <- list.back
                          ^
                         cur
```

而我们想要产生这样的结果：

```text
list.front -> C <-> D <- list.back
              ^
             cur

return.front -> A <-> B <- return.back
```

所以我们需要断开 cur 和 prev 之间的链接，然后……天哪要改的东西太多了。好吧，我得把它拆成一步步的，好说服自己这是说得通的。这会有点过于啰嗦，但至少我能理清楚：

```rust ,ignore
pub fn split_before(&mut self) -> LinkedList<T> {
    if let Some(cur) = self.cur {
        // We are pointing at a real element, so the list is non-empty.
        unsafe {
            // Current state
            let old_len = self.list.len;
            let old_idx = self.index.unwrap();
            let prev = (*cur.as_ptr()).front;
            
            // What self will become
            let new_len = old_len - old_idx;
            let new_front = self.cur;
            let new_back = self.list.back;
            let new_idx = Some(0);

            // What the output will become
            let output_len = old_len - new_len;
            let output_front = self.list.front;
            let output_back = prev;

            // Break the links between cur and prev
            if let Some(prev) = prev {
                (*cur.as_ptr()).front = None;
                (*prev.as_ptr()).back = None;
            }

            // Produce the result:
            self.list.len = new_len;
            self.list.front = new_front;
            self.list.back = new_back;
            self.index = new_idx;

            LinkedList {
                front: output_front,
                back: output_back,
                len: output_len,
                _boo: PhantomData,
            }
        }
    } else {
        // We're at the ghost, just replace our list with an empty one.
        // No other state needs to be changed.
        std::mem::replace(self.list, LinkedList::new())
    }
}
```

注意这个 if-let 处理的是“普通情形，但 prev 是幽灵”的状况：

```rust ,ignore
if let Some(prev) = prev {
    (*cur.as_ptr()).front = None;
    (*prev.as_ptr()).back = None;
}
```

如果*你*愿意，可以把这一切揉在一起，并施加一些优化，比如：

* 把对`(*cur.as_ptr()).front`的两次访问合并成一次`(*cur.as_ptr()).front.take()`
* 注意到 new_back 是个空操作，把它们两处都删掉

就我所见，其余一切都碰巧自然而然地做对了。等我们写测试时就知道了！（复制粘贴一下就能做出 split_after）

我不再犯错了，我要尽力写出我所能写出的最万无一失的代码。我*实际上*就是这么写集合的：把事情拆成一个个平凡的步骤和情形，直到它能装进我脑子里、看上去万无一失为止。然后写一大堆测试，直到我确信自己确实没能搞砸它。

因为我做过的大部分集合工作都是*极其不安全*的，我通常没法指望编译器替我抓错，而当年 miri 还不存在！所以我只能盯着一个问题眯眼盯到头疼，然后拼尽全力做到绝对绝对绝对不犯错。

别写不安全的 Rust 代码！安全 Rust 好太多了！！！！




# 拼接

只剩最后一个 boss 要打了：splice_before 和 splice_after，我预计它们会是所有这些里边角情形最多的。这两个函数*接收*一个 LinkedList，把它的内容嫁接进我们的链表。我们的链表可能是空的，他们的链表可能是空的，还有幽灵要应付……*叹气*我们还是拿 splice_before 一步一步来吧。

* 如果他们的链表是空的，我们什么都不用做。
* 如果我们的链表是空的，那我们的链表就变成他们的链表。
* 如果我们指向幽灵，那这就是往后端追加（改 list.back）
* 如果我们指向第一个元素（0），那这就是往前端追加（改 list.front）
* 在一般情形下，我们要做一大堆指针的鬼把戏。

一般情形是这样的：

```text
input.front -> 1 <-> 2 <- input.back

 list.front -> A <-> B <-> C <- list.back
                     ^
                    cur
```

要变成这样：

```text
list.front -> A <-> 1 <-> 2 <-> B <-> C <- list.back
```

行吗？行。我们把它写出来吧……*深吸一口气，一头扎进去*：

```rust ,ignore
    pub fn splice_before(&mut self, mut input: LinkedList<T>) {
        unsafe {
            if input.is_empty() {
                // Input is empty, do nothing.
            } else if let Some(cur) = self.cur {
                if let Some(0) = self.index {
                    // We're appending to the front, see append to back
                    (*cur.as_ptr()).front = input.back.take();
                    (*input.back.unwrap().as_ptr()).back = Some(cur);
                    self.list.front = input.front.take();

                    // Index moves forward by input length
                    *self.index.as_mut().unwrap() += input.len;
                    self.list.len += input.len;
                    input.len = 0;
                } else {
                    // General Case, no boundaries, just internal fixups
                    let prev = (*cur.as_ptr()).front.unwrap();
                    let in_front = input.front.take().unwrap();
                    let in_back = input.back.take().unwrap();

                    (*prev.as_ptr()).back = Some(in_front);
                    (*in_front.as_ptr()).front = Some(prev);
                    (*cur.as_ptr()).front = Some(in_back);
                    (*in_back.as_ptr()).back = Some(cur);

                    // Index moves forward by input length
                    *self.index.as_mut().unwrap() += input.len;
                    self.list.len += input.len;
                    input.len = 0;
                }
            } else if let Some(back) = self.list.back {
                // We're on the ghost but non-empty, append to the back
                // We can either `take` the input's pointers or `mem::forget`
                // it. Using take is more responsible in case we do custom
                // allocators or something that also needs to be cleaned up!
                (*back.as_ptr()).back = input.front.take();
                (*input.front.unwrap().as_ptr()).front = Some(back);
                self.list.back = input.back.take();
                self.list.len += input.len;
                // Not necessary but Polite To Do
                input.len = 0;
            } else {
                // We're empty, become the input, remain on the ghost
                *self.list = input;
            }
        }
    }
```

好吧，这一个是真的惨不忍睹，现在是真真切切地感受到了`Option<NonNull>`带来的痛苦。不过我们还能做很多清理。首先，我们可以把这段代码提到最末尾，因为我们总是要做它。我不*喜欢*（虽然有时候它是个空操作，而设置`input.len`更多是出于对代码未来扩展的疑神疑鬼）：

```rust ,ignore
self.list.len += input.len;
input.len = 0;
```

> Use of moved value: `input`

啊，对，在“我们是空的”那种情形里我们把链表移动走了。我们把它换成一次 swap：

```rust ,ignore
// We're empty, become the input, remain on the ghost
std::mem::swap(self.list, &mut input);
```

在这种情况下这些写入是没有意义的，但它们仍然是有效的（我们大概也可以在这个分支里提前返回来安抚编译器）。

这个 unwrap 不过是我把情形想反了的后果，只要让 if-let 问出正确的问题就能修好：

```rust ,ignore
if let Some(0) = self.index {

} else {
    let prev = (*cur.as_ptr()).front.unwrap();
}
```

调整索引的代码在各个分支里重复了，所以也可以提出来：

```rust
*self.index.as_mut().unwrap() += input.len;
```

好了，把这些合到一起我们就得到了这个：

```rust
if input.is_empty() {
    // Input is empty, do nothing.
} else if let Some(cur) = self.cur {
    // Both lists are non-empty
    if let Some(prev) = (*cur.as_ptr()).front {
        // General Case, no boundaries, just internal fixups
        let in_front = input.front.take().unwrap();
        let in_back = input.back.take().unwrap();

        (*prev.as_ptr()).back = Some(in_front);
        (*in_front.as_ptr()).front = Some(prev);
        (*cur.as_ptr()).front = Some(in_back);
        (*in_back.as_ptr()).back = Some(cur);
    } else {
        // We're appending to the front, see append to back below
        (*cur.as_ptr()).front = input.back.take();
        (*input.back.unwrap().as_ptr()).back = Some(cur);
        self.list.front = input.front.take();
    }
    // Index moves forward by input length
    *self.index.as_mut().unwrap() += input.len;
} else if let Some(back) = self.list.back {
    // We're on the ghost but non-empty, append to the back
    // We can either `take` the input's pointers or `mem::forget`
    // it. Using take is more responsible in case we do custom
    // allocators or something that also needs to be cleaned up!
    (*back.as_ptr()).back = input.front.take();
    (*input.front.unwrap().as_ptr()).front = Some(back);
    self.list.back = input.back.take();

} else {
    // We're empty, become the input, remain on the ghost
    std::mem::swap(self.list, &mut input);
}

self.list.len += input.len;
// Not necessary but Polite To Do
input.len = 0;

// Input dropped here
```

好吧这仍然很糟，不过主要是因为——不对，我刚发现一个 bug：

```rust
    (*back.as_ptr()).back = input.front.take();
    (*input.front.unwrap().as_ptr()).front = Some(back);
```

我们`take`了 input.front，然后在下一行又对它 unwrap！*叹气*而且在对称的那种情形里我们干了同样的事。这在测试里会被立刻抓住，可我们现在正努力做到完美，而我基本上是在直播写这个，这就是我看到它的确切时刻。这就是我没能保持一贯的啰嗦作风、没有分阶段行事的报应。再显式一点！

```rust
// We can either `take` the input's pointers or `mem::forget`
// it. Using `take` is more responsible in case we ever do custom
// allocators or something that also needs to be cleaned up!
if input.is_empty() {
    // Input is empty, do nothing.
} else if let Some(cur) = self.cur {
    // Both lists are non-empty
    let in_front = input.front.take().unwrap();
    let in_back = input.back.take().unwrap();

    if let Some(prev) = (*cur.as_ptr()).front {
        // General Case, no boundaries, just internal fixups
        (*prev.as_ptr()).back = Some(in_front);
        (*in_front.as_ptr()).front = Some(prev);
        (*cur.as_ptr()).front = Some(in_back);
        (*in_back.as_ptr()).back = Some(cur);
    } else {
        // No prev, we're appending to the front
        (*cur.as_ptr()).front = Some(in_back);
        (*in_back.as_ptr()).back = Some(cur);
        self.list.front = Some(in_front);
    }
    // Index moves forward by input length
    *self.index.as_mut().unwrap() += input.len;
} else if let Some(back) = self.list.back {
    // We're on the ghost but non-empty, append to the back
    let in_front = input.front.take().unwrap();
    let in_back = input.back.take().unwrap();

    (*back.as_ptr()).back = Some(in_front);
    (*in_front.as_ptr()).front = Some(back);
    self.list.back = Some(in_back);
} else {
    // We're empty, become the input, remain on the ghost
    std::mem::swap(self.list, &mut input);
}

self.list.len += input.len;
// Not necessary but Polite To Do
input.len = 0;

// Input dropped here
```

好了，现在这个，这个我能忍。我唯一的抱怨是我们没有把 in_front/in_back 去重（大概我们可以把条件重新捣鼓一下，不过嗨随便吧）。说真的，这基本上就是你在 C 里会写的东西，只是`Option<NonNull>`那堆玩意儿让它变得繁琐。这我能接受。嗯不对，我们其实该把原始指针在这类事情上做得更好用些。不过，那超出本书范围了。

总之，写完这些我已经彻底精疲力尽了，所以`insert`、`remove`以及其他所有 API 就留给读者作为练习吧。

下面是我们 Cursor 的最终代码，里边有我对那些组合情形的复制粘贴尝试。我做对了吗？只有等我写下一章、去测试这个怪物的时候才知道！


```rust ,ignore
pub struct CursorMut<'a, T> {
    list: &'a mut LinkedList<T>,
    cur: Link<T>,
    index: Option<usize>,
}

impl<T> LinkedList<T> {
    pub fn cursor_mut(&mut self) -> CursorMut<T> {
        CursorMut { 
            list: self, 
            cur: None, 
            index: None,
        }
    }
}

impl<'a, T> CursorMut<'a, T> {
    pub fn index(&self) -> Option<usize> {
        self.index
    }

    pub fn move_next(&mut self) {
        if let Some(cur) = self.cur {
            unsafe {
                // We're on a real element, go to its next (back)
                self.cur = (*cur.as_ptr()).back;
                if self.cur.is_some() {
                    *self.index.as_mut().unwrap() += 1;
                } else {
                    // We just walked to the ghost, no more index
                    self.index = None;
                }
            }
        } else if !self.list.is_empty() {
            // We're at the ghost, and there is a real front, so move to it!
            self.cur = self.list.front;
            self.index = Some(0)
        } else {
            // We're at the ghost, but that's the only element... do nothing.
        }
    }

    pub fn move_prev(&mut self) {
        if let Some(cur) = self.cur {
            unsafe {
                // We're on a real element, go to its previous (front)
                self.cur = (*cur.as_ptr()).front;
                if self.cur.is_some() {
                    *self.index.as_mut().unwrap() -= 1;
                } else {
                    // We just walked to the ghost, no more index
                    self.index = None;
                }
            }
        } else if !self.list.is_empty() {
            // We're at the ghost, and there is a real back, so move to it!
            self.cur = self.list.back;
            self.index = Some(self.list.len - 1)
        } else {
            // We're at the ghost, but that's the only element... do nothing.
        }
    }

    pub fn current(&mut self) -> Option<&mut T> {
        unsafe {
            self.cur.map(|node| &mut (*node.as_ptr()).elem)
        }
    }

    pub fn peek_next(&mut self) -> Option<&mut T> {
        unsafe {
            self.cur
                .and_then(|node| (*node.as_ptr()).back)
                .map(|node| &mut (*node.as_ptr()).elem)
        }
    }

    pub fn peek_prev(&mut self) -> Option<&mut T> {
        unsafe {
            self.cur
                .and_then(|node| (*node.as_ptr()).front)
                .map(|node| &mut (*node.as_ptr()).elem)
        }
    }

    pub fn split_before(&mut self) -> LinkedList<T> {
        // We have this:
        //
        //     list.front -> A <-> B <-> C <-> D <- list.back
        //                               ^
        //                              cur
        // 
        //
        // And we want to produce this:
        // 
        //     list.front -> C <-> D <- list.back
        //                   ^
        //                  cur
        //
        // 
        //    return.front -> A <-> B <- return.back
        //
        if let Some(cur) = self.cur {
            // We are pointing at a real element, so the list is non-empty.
            unsafe {
                // Current state
                let old_len = self.list.len;
                let old_idx = self.index.unwrap();
                let prev = (*cur.as_ptr()).front;
                
                // What self will become
                let new_len = old_len - old_idx;
                let new_front = self.cur;
                let new_back = self.list.back;
                let new_idx = Some(0);

                // What the output will become
                let output_len = old_len - new_len;
                let output_front = self.list.front;
                let output_back = prev;

                // Break the links between cur and prev
                if let Some(prev) = prev {
                    (*cur.as_ptr()).front = None;
                    (*prev.as_ptr()).back = None;
                }

                // Produce the result:
                self.list.len = new_len;
                self.list.front = new_front;
                self.list.back = new_back;
                self.index = new_idx;

                LinkedList {
                    front: output_front,
                    back: output_back,
                    len: output_len,
                    _boo: PhantomData,
                }
            }
        } else {
            // We're at the ghost, just replace our list with an empty one.
            // No other state needs to be changed.
            std::mem::replace(self.list, LinkedList::new())
        }
    }

    pub fn split_after(&mut self) -> LinkedList<T> {
        // We have this:
        //
        //     list.front -> A <-> B <-> C <-> D <- list.back
        //                         ^
        //                        cur
        // 
        //
        // And we want to produce this:
        // 
        //     list.front -> A <-> B <- list.back
        //                         ^
        //                        cur
        //
        // 
        //    return.front -> C <-> D <- return.back
        //
        if let Some(cur) = self.cur {
            // We are pointing at a real element, so the list is non-empty.
            unsafe {
                // Current state
                let old_len = self.list.len;
                let old_idx = self.index.unwrap();
                let next = (*cur.as_ptr()).back;
                
                // What self will become
                let new_len = old_idx + 1;
                let new_back = self.cur;
                let new_front = self.list.front;
                let new_idx = Some(old_idx);

                // What the output will become
                let output_len = old_len - new_len;
                let output_front = next;
                let output_back = self.list.back;

                // Break the links between cur and next
                if let Some(next) = next {
                    (*cur.as_ptr()).back = None;
                    (*next.as_ptr()).front = None;
                }

                // Produce the result:
                self.list.len = new_len;
                self.list.front = new_front;
                self.list.back = new_back;
                self.index = new_idx;

                LinkedList {
                    front: output_front,
                    back: output_back,
                    len: output_len,
                    _boo: PhantomData,
                }
            }
        } else {
            // We're at the ghost, just replace our list with an empty one.
            // No other state needs to be changed.
            std::mem::replace(self.list, LinkedList::new())
        }
    }

    pub fn splice_before(&mut self, mut input: LinkedList<T>) {
        // We have this:
        //
        // input.front -> 1 <-> 2 <- input.back
        //
        // list.front -> A <-> B <-> C <- list.back
        //                     ^
        //                    cur
        //
        //
        // Becoming this:
        //
        // list.front -> A <-> 1 <-> 2 <-> B <-> C <- list.back
        //                                 ^
        //                                cur
        //
        unsafe {
            // We can either `take` the input's pointers or `mem::forget`
            // it. Using `take` is more responsible in case we ever do custom
            // allocators or something that also needs to be cleaned up!
            if input.is_empty() {
                // Input is empty, do nothing.
            } else if let Some(cur) = self.cur {
                // Both lists are non-empty
                let in_front = input.front.take().unwrap();
                let in_back = input.back.take().unwrap();

                if let Some(prev) = (*cur.as_ptr()).front {
                    // General Case, no boundaries, just internal fixups
                    (*prev.as_ptr()).back = Some(in_front);
                    (*in_front.as_ptr()).front = Some(prev);
                    (*cur.as_ptr()).front = Some(in_back);
                    (*in_back.as_ptr()).back = Some(cur);
                } else {
                    // No prev, we're appending to the front
                    (*cur.as_ptr()).front = Some(in_back);
                    (*in_back.as_ptr()).back = Some(cur);
                    self.list.front = Some(in_front);
                }
                // Index moves forward by input length
                *self.index.as_mut().unwrap() += input.len;
            } else if let Some(back) = self.list.back {
                // We're on the ghost but non-empty, append to the back
                let in_front = input.front.take().unwrap();
                let in_back = input.back.take().unwrap();

                (*back.as_ptr()).back = Some(in_front);
                (*in_front.as_ptr()).front = Some(back);
                self.list.back = Some(in_back);
            } else {
                // We're empty, become the input, remain on the ghost
                std::mem::swap(self.list, &mut input);
            }

            self.list.len += input.len;
            // Not necessary but Polite To Do
            input.len = 0;
            
            // Input dropped here
        }        
    }

    pub fn splice_after(&mut self, mut input: LinkedList<T>) {
        // We have this:
        //
        // input.front -> 1 <-> 2 <- input.back
        //
        // list.front -> A <-> B <-> C <- list.back
        //                     ^
        //                    cur
        //
        //
        // Becoming this:
        //
        // list.front -> A <-> B <-> 1 <-> 2 <-> C <- list.back
        //                     ^
        //                    cur
        //
        unsafe {
            // We can either `take` the input's pointers or `mem::forget`
            // it. Using `take` is more responsible in case we ever do custom
            // allocators or something that also needs to be cleaned up!
            if input.is_empty() {
                // Input is empty, do nothing.
            } else if let Some(cur) = self.cur {
                // Both lists are non-empty
                let in_front = input.front.take().unwrap();
                let in_back = input.back.take().unwrap();

                if let Some(next) = (*cur.as_ptr()).back {
                    // General Case, no boundaries, just internal fixups
                    (*next.as_ptr()).front = Some(in_back);
                    (*in_back.as_ptr()).back = Some(next);
                    (*cur.as_ptr()).back = Some(in_front);
                    (*in_front.as_ptr()).front = Some(cur);
                } else {
                    // No next, we're appending to the back
                    (*cur.as_ptr()).back = Some(in_front);
                    (*in_front.as_ptr()).front = Some(cur);
                    self.list.back = Some(in_back);
                }
                // Index doesn't change
            } else if let Some(front) = self.list.front {
                // We're on the ghost but non-empty, append to the front
                let in_front = input.front.take().unwrap();
                let in_back = input.back.take().unwrap();

                (*front.as_ptr()).front = Some(in_back);
                (*in_back.as_ptr()).back = Some(front);
                self.list.front = Some(in_front);
            } else {
                // We're empty, become the input, remain on the ghost
                std::mem::swap(self.list, &mut input);
            }

            self.list.len += input.len;
            // Not necessary but Polite To Do
            input.len = 0;
            
            // Input dropped here
        }        
    }
}
```